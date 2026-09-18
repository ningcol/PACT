#!/usr/bin/env python3
"""Validate a PACT Evidence Receipt and determine completion readiness."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = ROOT / ".pact" / "schema" / "evidence-receipt.schema.json"


def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(receipt: dict) -> list[str]:
    validator = Draft202012Validator(load(SCHEMA))
    errors = []
    for err in sorted(validator.iter_errors(receipt), key=lambda e: list(e.path)):
        loc = ".".join(str(p) for p in err.path)
        errors.append(f"{loc or '<root>'}: {err.message}")
    return errors


def readiness(receipt: dict) -> str:
    required = [c for c in receipt.get("claims", []) if c.get("required")]
    if any(c.get("status") == "fail" for c in required):
        return "failed"
    if any(c.get("status") == "unverified" for c in required):
        return "incomplete"
    return "ready"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a PACT evidence receipt")
    parser.add_argument("receipt")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    path = pathlib.Path(args.receipt)
    if not path.is_absolute():
        path = ROOT / path

    try:
        receipt = load(path)
    except Exception as exc:
        print(f"PACT evidence: cannot read receipt: {exc}", file=sys.stderr)
        return 2

    errors = validate(receipt)
    if errors:
        print("PACT evidence: invalid receipt", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    state = readiness(receipt)
    result = {
        "task": receipt["task"],
        "risk_level": receipt["risk_level"],
        "readiness": state,
        "required_claims": len([c for c in receipt["claims"] if c["required"]]),
        "limitations": receipt["limitations"],
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"PACT evidence: {state}")
        print(f"Task: {result['task']}")
        for claim in receipt["claims"]:
            marker = "*" if claim["required"] else "-"
            print(f"{marker} [{claim['status']}] {claim['id']}: {claim['claim']}")
        if receipt["limitations"]:
            print("Limitations:")
            for limitation in receipt["limitations"]:
                print(f"- {limitation}")

    return 0 if state == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
