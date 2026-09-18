#!/usr/bin/env python3
"""Validate and expose the PACT Owner Profile."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import yaml
from jsonschema import Draft202012Validator


def load_yaml(path: pathlib.Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("configuration root must be an object")
    return data


def validate(config: dict, schema_path: pathlib.Path) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(config), key=lambda e: list(e.path)):
        loc = ".".join(str(p) for p in err.path)
        errors.append(f"{loc or '<root>'}: {err.message}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Read and validate the PACT Owner Profile")
    parser.add_argument("--root", help="repository root; defaults to this script's repository")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="require .pact/config.yaml rather than falling back to config.example.yaml",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    default_root = pathlib.Path(__file__).resolve().parents[2]
    root = pathlib.Path(args.root).expanduser().resolve() if args.root else default_root

    schema_path = root / ".pact" / "schema" / "config.schema.json"
    config_path = root / ".pact" / "config.yaml"
    example_path = root / ".pact" / "config.example.yaml"

    if not schema_path.exists():
        print(f"PACT owner: missing config schema at {schema_path}", file=sys.stderr)
        return 2

    configured = config_path.exists()
    if configured:
        source = config_path
    elif not args.strict and example_path.exists():
        source = example_path
    else:
        print("PACT owner: .pact/config.yaml is missing", file=sys.stderr)
        return 2

    try:
        config = load_yaml(source)
    except Exception as exc:
        print(f"PACT owner: cannot parse {source}: {exc}", file=sys.stderr)
        return 2

    errors = validate(config, schema_path)
    if errors:
        print(f"PACT owner: invalid configuration in {source}", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    owner = config["owner"]
    result = {
        "configured": configured,
        "source": source.relative_to(root).as_posix(),
        "role": owner["role"],
        "language": owner["language"],
        "technical_depth": owner["technical_depth"],
        "communication": owner["communication"],
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        state = "project config" if configured else "example fallback"
        print(f"PACT owner profile: {state}")
        print(f"- role: {result['role']}")
        print(f"- language: {result['language']}")
        print(f"- technical depth: {result['technical_depth']}")
        print(
            "- decision translation: "
            f"{result['communication']['decision_translation']}"
        )
        print(
            "- progressive disclosure: "
            f"{result['communication']['progressive_disclosure']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
