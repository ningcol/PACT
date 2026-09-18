#!/usr/bin/env python3
"""Validate a PACT Evidence Receipt, provenance, and completion readiness."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from schema_validate import load_schema, validate_instance


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = ROOT / ".pact" / "schema" / "evidence-receipt.schema.json"
RUN_SCHEMA = ROOT / ".pact" / "schema" / "run-receipt.schema.json"


def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(receipt: dict) -> list[str]:
    return validate_instance(receipt, load_schema(SCHEMA))


def resolve_ref(root: pathlib.Path, ref: str) -> pathlib.Path:
    path = pathlib.Path(ref).expanduser()
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def verify_item(
    item: dict,
    *,
    task_id: str,
    claim_status: str,
    root: pathlib.Path,
) -> tuple[list[str], bool]:
    provenance = item.get("provenance")
    kind = item.get("kind")
    ref = item.get("ref", "")
    errors: list[str] = []

    if provenance == "manual":
        if kind != "manual":
            errors.append(
                f"manual provenance requires kind 'manual', found {kind!r}"
            )
        return errors, False

    path = resolve_ref(root, ref)
    if not path.exists() or not path.is_file():
        return [f"evidence ref does not exist as a file: {ref}"], False

    if provenance == "file":
        if kind == "manual":
            errors.append("manual evidence kind cannot use file provenance")
        return errors, True

    if provenance == "pact-run":
        try:
            run_receipt = load(path)
        except Exception as exc:
            return [f"cannot read PACT run receipt {ref}: {exc}"], False

        schema_errors = validate_instance(run_receipt, load_schema(RUN_SCHEMA))
        errors.extend(f"run receipt {ref}: {error}" for error in schema_errors)
        if schema_errors:
            return errors, False

        if run_receipt.get("task_id") != task_id:
            errors.append(
                f"run receipt {ref} task_id {run_receipt.get('task_id')!r} "
                f"does not match evidence task_id {task_id!r}"
            )

        if claim_status == "pass" and run_receipt.get("status") != "pass":
            errors.append(
                f"pass claim references non-passing run receipt {ref}"
            )
        if claim_status == "fail" and run_receipt.get("status") != "fail":
            errors.append(
                f"fail claim references non-failing run receipt {ref}"
            )

        return errors, not errors

    return [f"unsupported provenance {provenance!r}"], False


def provenance_review(receipt: dict, root: pathlib.Path) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    policy_gaps: list[str] = []
    machine_backed_claims = 0

    task_id = receipt["task_id"]
    risk = receipt["risk_level"]

    for claim in receipt.get("claims", []):
        claim_id = claim["id"]
        status = claim["status"]
        refs = claim.get("evidence", [])

        if status in {"pass", "fail"} and not refs:
            errors.append(f"{claim_id}: {status} claim has no evidence")
            continue

        machine_count = 0
        for index, item in enumerate(refs):
            item_errors, machine_backed = verify_item(
                item,
                task_id=task_id,
                claim_status=status,
                root=root,
            )
            errors.extend(
                f"{claim_id}.evidence[{index}]: {error}"
                for error in item_errors
            )
            if machine_backed:
                machine_count += 1

        if machine_count:
            machine_backed_claims += 1

        if (
            claim.get("required")
            and status == "pass"
            and risk in {"medium", "high"}
            and machine_count == 0
        ):
            policy_gaps.append(
                f"{claim_id}: {risk}-risk required pass claim needs at least "
                "one machine-backed pact-run/file evidence source"
            )

    return errors, policy_gaps, {
        "machine_backed_claims": machine_backed_claims,
        "claim_count": len(receipt.get("claims", [])),
    }


def readiness(receipt: dict, policy_gaps: list[str] | None = None) -> str:
    required = [c for c in receipt.get("claims", []) if c.get("required")]
    if any(c.get("status") == "fail" for c in required):
        return "failed"
    if any(c.get("status") == "unverified" for c in required):
        return "incomplete"
    if policy_gaps:
        return "incomplete"
    return "ready"


def review(receipt: dict, root: pathlib.Path = ROOT) -> tuple[list[str], list[str], dict]:
    schema_errors = validate(receipt)
    if schema_errors:
        return schema_errors, [], {"machine_backed_claims": 0, "claim_count": 0}
    return provenance_review(receipt, root)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a PACT evidence receipt")
    parser.add_argument("receipt")
    parser.add_argument(
        "--root",
        help="repository root used to resolve evidence refs; defaults to PACT project root",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = pathlib.Path(args.root).expanduser().resolve() if args.root else ROOT
    path = pathlib.Path(args.receipt)
    if not path.is_absolute():
        path = root / path

    try:
        receipt = load(path)
    except Exception as exc:
        print(f"PACT evidence: cannot read receipt: {exc}", file=sys.stderr)
        return 2

    schema_errors = validate(receipt)
    if schema_errors:
        print("PACT evidence: invalid receipt", file=sys.stderr)
        for error in schema_errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    provenance_errors, policy_gaps, stats = provenance_review(receipt, root)
    if provenance_errors:
        print("PACT evidence: invalid provenance", file=sys.stderr)
        for error in provenance_errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    state = readiness(receipt, policy_gaps)
    result = {
        "task_id": receipt["task_id"],
        "task": receipt["task"],
        "risk_level": receipt["risk_level"],
        "readiness": state,
        "required_claims": len([c for c in receipt["claims"] if c["required"]]),
        "machine_backed_claims": stats["machine_backed_claims"],
        "policy_gaps": policy_gaps,
        "limitations": receipt["limitations"],
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"PACT evidence: {state}")
        print(f"Task: {result['task']} ({result['task_id']})")
        for claim in receipt["claims"]:
            marker = "*" if claim["required"] else "-"
            print(f"{marker} [{claim['status']}] {claim['id']}: {claim['claim']}")
        if policy_gaps:
            print("Policy gaps:")
            for gap in policy_gaps:
                print(f"- {gap}")
        if receipt["limitations"]:
            print("Limitations:")
            for limitation in receipt["limitations"]:
                print(f"- {limitation}")

    return 0 if state == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
