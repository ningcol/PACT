#!/usr/bin/env python3
"""Deterministic PACT repository checks.

Checks only facts a machine can establish reliably:
- PACT front matter/schema
- stable ID uniqueness and local reference integrity
- known lifecycle values
- artifact type/path compatibility
- lifecycle directory/status compatibility
- resolvable internal Markdown links

Semantic drift belongs to Convergence Review, not this script.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import dataclass
from urllib.parse import unquote

try:
    import yaml
    from jsonschema import Draft202012Validator
except ImportError as exc:
    print(
        "Missing PACT check dependencies. Run: "
        "python -m pip install -r scripts/pact/requirements.txt",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc


STATUS_BY_TYPE = {
    "domain": {"candidate", "confirmed", "superseded", "retired"},
    "rule": {"candidate", "confirmed", "superseded", "retired"},
    "decision": {"proposed", "implemented", "rejected", "superseded", "archived"},
    "change": {"active", "completed", "abandoned"},
    "drift": {"known", "resolved", "accepted"},
    "architecture": {"current", "deprecated"},
}

PATH_PREFIX_BY_TYPE = {
    "domain": ("docs/product/domains/",),
    "rule": ("docs/product/rules/",),
    "decision": (".agents/decisions/",),
    "change": ("docs/changes/",),
    "drift": ("docs/drift/",),
    "architecture": ("docs/architecture/",),
}

ID_REQUIRED = {"domain", "rule", "decision", "drift"}

FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
EXTERNAL_PREFIXES = (
    "http://",
    "https://",
    "mailto:",
    "tel:",
    "data:",
    "javascript:",
)

MANAGED_ROOT_FILES = {"README.md", "AGENTS.md"}
MANAGED_PREFIXES = ("docs/", ".agents/")


@dataclass
class Artifact:
    path: pathlib.Path
    pact: dict


def rel(path: pathlib.Path, root: pathlib.Path) -> str:
    return path.relative_to(root).as_posix()


def is_managed_markdown(path: pathlib.Path, root: pathlib.Path) -> bool:
    relative = rel(path, root)
    return (
        relative in MANAGED_ROOT_FILES
        or relative.startswith(MANAGED_PREFIXES)
    )


def load_schema(root: pathlib.Path) -> dict:
    return json.loads(
        (root / ".pact" / "schema" / "artifact.schema.json").read_text(encoding="utf-8")
    )


def read_artifact(path: pathlib.Path) -> Artifact | None:
    text = path.read_text(encoding="utf-8")
    match = FRONT_MATTER.match(text)
    if not match:
        return None

    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict) or "pact" not in data:
        return None

    pact = data.get("pact")
    if not isinstance(pact, dict):
        raise ValueError("front matter key 'pact' must be an object")

    return Artifact(path=path, pact=pact)


def discover(root: pathlib.Path) -> tuple[list[Artifact], list[str]]:
    artifacts: list[Artifact] = []
    errors: list[str] = []

    for path in sorted(root.rglob("*.md")):
        if not is_managed_markdown(path, root):
            continue
        relative = rel(path, root)
        if relative.endswith("/TEMPLATE.md") or relative == "TEMPLATE.md":
            continue
        try:
            artifact = read_artifact(path)
            if artifact:
                artifacts.append(artifact)
        except Exception as exc:
            errors.append(f"{relative}: invalid PACT front matter: {exc}")

    return artifacts, errors


def lifecycle_errors(path: str, typ: str | None, status: str | None) -> list[str]:
    errors: list[str] = []

    if typ == "decision":
        if "/proposed/" in path and status != "proposed":
            errors.append(f"{path}: proposed decision path requires status 'proposed'")
        if "/implemented/" in path and status not in {"implemented", "superseded"}:
            errors.append(
                f"{path}: implemented decision path requires status 'implemented' or 'superseded'"
            )
        if "/rejected/" in path and status != "rejected":
            errors.append(f"{path}: rejected decision path requires status 'rejected'")
        if "/archived/" in path and status != "archived":
            errors.append(f"{path}: archived decision path requires status 'archived'")

    if typ == "drift":
        if "/known/" in path and status != "known":
            errors.append(f"{path}: known drift path requires status 'known'")
        if "/resolved/" in path and status != "resolved":
            errors.append(f"{path}: resolved drift path requires status 'resolved'")
        if "/accepted/" in path and status != "accepted":
            errors.append(f"{path}: accepted drift path requires status 'accepted'")

    if typ == "change":
        if "/active/" in path and status != "active":
            errors.append(f"{path}: active change path requires status 'active'")
        if "/completed/" in path and status != "completed":
            errors.append(f"{path}: completed change path requires status 'completed'")
        if "/abandoned/" in path and status != "abandoned":
            errors.append(f"{path}: abandoned change path requires status 'abandoned'")

    return errors


def validate_artifacts(artifacts: list[Artifact], root: pathlib.Path) -> list[str]:
    errors: list[str] = []
    validator = Draft202012Validator(load_schema(root))
    seen_ids: dict[str, Artifact] = {}

    # First pass: local shape, lifecycle, and ID inventory.
    for artifact in artifacts:
        path = rel(artifact.path, root)
        wrapper = {"pact": artifact.pact}

        for err in sorted(validator.iter_errors(wrapper), key=lambda e: list(e.path)):
            loc = ".".join(str(part) for part in err.path)
            errors.append(f"{path}: schema error at {loc or '<root>'}: {err.message}")

        typ = artifact.pact.get("type")
        status = artifact.pact.get("status")
        ident = artifact.pact.get("id")

        if typ in ID_REQUIRED and not ident:
            errors.append(f"{path}: type '{typ}' requires a stable id")

        if ident:
            previous = seen_ids.get(ident)
            if previous:
                errors.append(
                    f"{path}: duplicate stable id '{ident}' already used by "
                    f"{rel(previous.path, root)}"
                )
            else:
                seen_ids[ident] = artifact

        if typ in STATUS_BY_TYPE and status is not None and status not in STATUS_BY_TYPE[typ]:
            allowed = ", ".join(sorted(STATUS_BY_TYPE[typ]))
            errors.append(
                f"{path}: invalid status '{status}' for type '{typ}' (allowed: {allowed})"
            )

        prefixes = PATH_PREFIX_BY_TYPE.get(typ)
        if prefixes and not path.startswith(prefixes):
            errors.append(
                f"{path}: type '{typ}' must live under one of: {', '.join(prefixes)}"
            )

        errors.extend(lifecycle_errors(path, typ, status))

    # Second pass: references need the complete ID inventory.
    for artifact in artifacts:
        path = rel(artifact.path, root)
        typ = artifact.pact.get("type")
        ident = artifact.pact.get("id")

        for domain_id in artifact.pact.get("domains", []) or []:
            target = seen_ids.get(domain_id)
            if not target:
                errors.append(f"{path}: domains references missing id '{domain_id}'")
            elif target.pact.get("type") != "domain":
                errors.append(
                    f"{path}: domains reference '{domain_id}' must target type 'domain', "
                    f"found '{target.pact.get('type')}'"
                )

        for field in ("related", "supersedes"):
            for target_id in artifact.pact.get(field, []) or []:
                target = seen_ids.get(target_id)
                if not target:
                    errors.append(f"{path}: {field} references missing id '{target_id}'")
                    continue
                if target_id == ident:
                    errors.append(f"{path}: {field} must not reference itself ('{target_id}')")
                if field == "supersedes" and target.pact.get("type") != typ:
                    errors.append(
                        f"{path}: supersedes '{target_id}' must target the same artifact type"
                    )

        superseded_by = artifact.pact.get("superseded_by")
        if superseded_by:
            target = seen_ids.get(superseded_by)
            if not target:
                errors.append(
                    f"{path}: superseded_by references missing id '{superseded_by}'"
                )
            else:
                if superseded_by == ident:
                    errors.append(
                        f"{path}: superseded_by must not reference itself ('{superseded_by}')"
                    )
                if target.pact.get("type") != typ:
                    errors.append(
                        f"{path}: superseded_by '{superseded_by}' must target the same artifact type"
                    )

    return errors


def clean_link(raw: str) -> str:
    value = raw.strip()
    if value.startswith("<") and value.endswith(">"):
        value = value[1:-1].strip()
    # Markdown destination may contain a title after whitespace; PACT docs use simple paths.
    if " " in value and not value.startswith(("http://", "https://")):
        value = value.split(" ", 1)[0]
    return unquote(value)


def validate_links(root: pathlib.Path) -> list[str]:
    errors: list[str] = []
    root_resolved = root.resolve()

    for path in sorted(root.rglob("*.md")):
        if not is_managed_markdown(path, root):
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for raw in MD_LINK.findall(text):
            link = clean_link(raw)
            if not link or link.startswith("#") or link.startswith(EXTERNAL_PREFIXES):
                continue

            destination = link.split("#", 1)[0].split("?", 1)[0]
            if not destination:
                continue

            if destination.startswith("/"):
                target = root / destination.lstrip("/")
            else:
                target = path.parent / destination

            resolved = target.resolve()
            if resolved != root_resolved and root_resolved not in resolved.parents:
                errors.append(
                    f"{rel(path, root)}: internal link escapes repository: '{raw}'"
                )
                continue

            if not resolved.exists():
                errors.append(
                    f"{rel(path, root)}: broken internal link '{raw}'"
                )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic PACT checks")
    parser.add_argument(
        "--root",
        help="repository root to validate; defaults to the repository containing this script",
    )
    args = parser.parse_args()

    default_root = pathlib.Path(__file__).resolve().parents[2]
    root = pathlib.Path(args.root).expanduser().resolve() if args.root else default_root

    schema = root / ".pact" / "schema" / "artifact.schema.json"
    if not schema.exists():
        print(f"PACT: missing artifact schema at {schema}", file=sys.stderr)
        return 2

    artifacts, errors = discover(root)
    errors.extend(validate_artifacts(artifacts, root))
    errors.extend(validate_links(root))

    print(f"PACT: discovered {len(artifacts)} machine-readable artifact(s).")

    if errors:
        print(f"PACT: {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("PACT: deterministic checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
