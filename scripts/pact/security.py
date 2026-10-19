"""Secret redaction helpers for persisted PACT execution metadata."""

from __future__ import annotations

import os
import re


SENSITIVE_OPTION = re.compile(
    r"^--?(?:"
    r"token|access[-_]?token|auth[-_]?token|authorization|"
    r"password|passwd|secret|client[-_]?secret|"
    r"api[-_]?key|apikey|private[-_]?key"
    r")$",
    re.IGNORECASE,
)

SENSITIVE_ASSIGNMENT = re.compile(
    r"^(--?(?:"
    r"token|access[-_]?token|auth[-_]?token|authorization|"
    r"password|passwd|secret|client[-_]?secret|"
    r"api[-_]?key|apikey|private[-_]?key"
    r"))=(.*)$",
    re.IGNORECASE,
)

AUTH_HEADER = re.compile(r"(?i)(authorization\s*:\s*)(.+)$")

SECRET_ENV_NAME = re.compile(
    r"(TOKEN|SECRET|PASSWORD|PASSWD|API[_-]?KEY|AUTHORIZATION|PRIVATE[_-]?KEY|CLIENT[_-]?SECRET)",
    re.IGNORECASE,
)


def secret_environment_values() -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    for name, value in os.environ.items():
        if not value or len(value) < 4:
            continue
        if SECRET_ENV_NAME.search(name):
            values.append((name, value))
    values.sort(key=lambda item: len(item[1]), reverse=True)
    return values


def redact_argv(
    argv: list[str],
    *,
    extra_values: list[str] | None = None,
    detailed: bool = False,
) -> tuple[list[str], int]:
    """Default to NOT persisting any executed command arguments.

    Regex filtering can never prove that custom HTTP headers, JSON payloads,
    bespoke credential flags or command names contain no secret. PACT Evidence
    requires exit status/output digests, not argv, so full argument omission is
    the only safe automatic persistence policy. `detailed=True` is for
    trusted local diagnostic callers; PACT's run receipt never enables it.
    """
    if not detailed:
        return ["<redacted: command arguments omitted>"], len(argv)

    redacted: list[str] = []
    count = 0
    hide_next = False
    env_values = secret_environment_values()
    literals = [value for value in (extra_values or []) if value]

    for raw in argv:
        value = raw

        if hide_next:
            redacted.append("<redacted>")
            hide_next = False
            count += 1
            continue

        if SENSITIVE_OPTION.match(value):
            redacted.append(value)
            hide_next = True
            continue

        match = SENSITIVE_ASSIGNMENT.match(value)
        if match:
            redacted.append(f"{match.group(1)}=<redacted>")
            count += 1
            continue

        header = AUTH_HEADER.search(value)
        if header:
            value = (
                value[: header.start()]
                + header.group(1)
                + "<redacted>"
            )
            count += 1

        for name, secret in env_values:
            if secret in value:
                value = value.replace(secret, f"<redacted-env:{name}>")
                count += 1

        for secret in literals:
            if secret in value:
                value = value.replace(secret, "<redacted>")
                count += 1

        redacted.append(value)

    return redacted, count
