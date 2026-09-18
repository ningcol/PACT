#!/usr/bin/env python3
"""Deterministic PACT repository checks.

This intentionally checks only facts a machine can establish reliably:
- PACT front matter shape
- stable ID uniqueness
- known lifecycle values
- artifact type/path compatibility
- DOMAIN references use canonical ID shape

Semantic drift belongs to convergence review, not this script.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import dataclass

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


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / ".pact" / "schema" / "artifact.schema.json"

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


@dataclass
class Artifact:
    path: pathlib.Path
    pact: dict


def rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


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


def discover() -> tuple[list[Artifact], list[str]]:
    artifacts: list[Artifact] = []
    errors: list[str] = []

    for path in sorted(ROOT.rglob("*.md")):
        if any(part in {".git", ".pact/cache"} for part in path.parts):
            continue
        try:
            artifact = read_artifact(path)
            if artifact:
                artifacts.append(artifact)
        except Exception as exc:  # deterministic parse failure
            errors.append(f"{rel(path)}: invalid PACT front matter: {exc}")

    return artifacts, errors


def validate_artifacts(artifacts: list[Artifact]) -> list[str]:
    errors: list[str] = []
    validator = Draft202012Validator(load_schema())
    seen_ids: dict[str, str] = {}

    for artifact in artifacts:
        path = rel(artifact.path)
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
                errors.append(f"{path}: duplicate stable id '{ident}' already used by {previous}")
            else:
                seen_ids[ident] = path

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

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic PACT checks")
    parser.parse_args()

    artifacts, errors = discover()
    errors.extend(validate_artifacts(artifacts))

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
