#!/usr/bin/env python3
"""Validate a complete PACT task completion bundle."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from evidence import (
    provenance_review,
    readiness as evidence_readiness,
    validate as validate_evidence,
)
from report import (
    CONVERGENCE_SCHEMA,
    OWNER_SCHEMA,
    convergence_outcome,
    cross_validate,
    validate as validate_report_part,
)


ROOT = pathlib.Path(__file__).resolve().parents[2]


def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Evidence + Convergence + Owner Report as one completion gate"
    )
    parser.add_argument(
        "bundle",
        help="directory containing evidence.json, convergence.json, owner-report.json",
    )
    parser.add_argument(
        "--root",
        help="repository root used to resolve Evidence provenance refs",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = pathlib.Path(args.root).expanduser().resolve() if args.root else ROOT
    bundle = pathlib.Path(args.bundle).expanduser()
    if not bundle.is_absolute():
        bundle = root / bundle
    bundle = bundle.resolve()

    files = {
        "evidence": bundle / "evidence.json",
        "convergence": bundle / "convergence.json",
        "owner": bundle / "owner-report.json",
    }

    missing = [name for name, path in files.items() if not path.is_file()]
    if missing:
        print(
            "PACT complete: missing bundle file(s): " + ", ".join(missing),
            file=sys.stderr,
        )
        return 2

    try:
        evidence = load(files["evidence"])
        convergence = load(files["convergence"])
        owner = load(files["owner"])
    except Exception as exc:
        print(f"PACT complete: cannot read bundle: {exc}", file=sys.stderr)
        return 2

    errors: list[str] = []
    errors.extend(f"evidence.{error}" for error in validate_evidence(evidence))
    errors.extend(validate_report_part(convergence, CONVERGENCE_SCHEMA, "convergence"))
    errors.extend(validate_report_part(owner, OWNER_SCHEMA, "owner"))

    policy_gaps: list[str] = []
    if not errors:
        provenance_errors, policy_gaps, _ = provenance_review(evidence, root)
        errors.extend(
            f"evidence provenance: {error}"
            for error in provenance_errors
        )
        errors.extend(cross_validate(owner, evidence, convergence, root=root))

    risk = evidence.get("risk_level")
    evidence_state = (
        evidence_readiness(evidence, policy_gaps)
        if not errors
        else "invalid"
    )
    convergence_state = (
        convergence_outcome(convergence)
        if not errors
        else "invalid"
    )

    if not errors and owner.get("status") != "completed":
        errors.append(
            f"completion bundle owner status must be 'completed', "
            f"found {owner.get('status')!r}"
        )

    if not errors and evidence_state != "ready":
        errors.append(
            f"completion bundle Evidence is not ready ({evidence_state})"
        )

    if not errors and convergence_state in {"needs-reconciliation", "needs-owner"}:
        errors.append(
            f"completion bundle Convergence is blocking ({convergence_state})"
        )

    if not errors and risk == "high":
        if evidence.get("limitations"):
            errors.append(
                "high-risk completion cannot carry unresolved Evidence limitations"
            )
        if convergence_state != "aligned":
            errors.append(
                "high-risk completion requires fully aligned Convergence; "
                f"found {convergence_state}"
            )

    result = {
        "task_id": evidence.get("task_id"),
        "risk_level": risk,
        "evidence": evidence_state,
        "convergence": convergence_state,
        "owner_status": owner.get("status"),
        "complete": not errors,
        "errors": errors,
        "policy_gaps": policy_gaps,
        "bundle": str(bundle),
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"PACT complete: {'PASS' if result['complete'] else 'FAIL'}")
        print(f"- task: {result['task_id']}")
        print(f"- risk: {risk}")
        print(f"- evidence: {evidence_state}")
        print(f"- convergence: {convergence_state}")
        print(f"- owner status: {owner.get('status')}")
        if policy_gaps:
            print("Policy gaps:")
            for gap in policy_gaps:
                print(f"- {gap}")
        if errors:
            print("Errors:")
            for error in errors:
                print(f"- {error}")

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
