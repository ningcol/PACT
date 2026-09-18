#!/usr/bin/env python3
"""Validate and summarize optional PACT pilot evaluation records."""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys
from collections import defaultdict

from jsonschema import Draft202012Validator


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = ROOT / ".pact" / "schema" / "pilot-evaluation.schema.json"


def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(record: dict) -> list[str]:
    schema = load(SCHEMA)
    validator = Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(record), key=lambda e: list(e.path)):
        loc = ".".join(str(p) for p in err.path)
        errors.append(f"{loc or '<root>'}: {err.message}")
    return errors


def aggregate(records: list[dict]) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        groups[record["mode"]].append(record)

    summary = {}

    for mode, items in sorted(groups.items()):
        count = len(items)
        tech_escalations = sum(
            item["owner_interactions"]["technical_escalations"]
            for item in items
        )
        product_decisions = sum(
            item["owner_interactions"]["product_decisions"]
            for item in items
        )
        clarifications = sum(
            item["owner_interactions"]["clarification_rounds"]
            for item in items
        )
        clear_count = sum(
            item["owner_interactions"]["comprehension"] == "clear"
            for item in items
        )
        done_blocked = sum(
            item["completion_integrity"]["unsupported_done_claims_blocked"]
            for item in items
        )
        evidence_gaps = sum(
            item["completion_integrity"]["evidence_gaps_found"]
            for item in items
        )
        convergence = sum(
            item["completion_integrity"]["convergence_findings"]
            for item in items
        )
        explain_used = [
            item["project_memory"]["explain_outcome"]
            for item in items
            if item["project_memory"]["explain_used"]
        ]
        explain_resolved = sum(value == "resolved" for value in explain_used)
        overload = sum(
            item["context_quality"]["overload_observed"]
            for item in items
        )
        overhead = [
            float(item["pact_overhead_minutes"])
            for item in items
            if item.get("pact_overhead_minutes") is not None
        ]

        summary[mode] = {
            "task_count": count,
            "completed": sum(item["outcome"] == "completed" for item in items),
            "product_decisions": product_decisions,
            "technical_escalations": tech_escalations,
            "clarification_rounds": clarifications,
            "owner_clear_rate": clear_count / count if count else None,
            "unsupported_done_claims_blocked": done_blocked,
            "evidence_gaps_found": evidence_gaps,
            "convergence_findings": convergence,
            "explain_uses": len(explain_used),
            "explain_resolved_rate": (
                explain_resolved / len(explain_used)
                if explain_used
                else None
            ),
            "context_overload_tasks": overload,
            "mean_knowledge_artifacts": statistics.fmean(
                item["context_quality"]["knowledge_artifacts"]
                for item in items
            ) if items else None,
            "mean_code_artifacts": statistics.fmean(
                item["context_quality"]["code_artifacts"]
                for item in items
            ) if items else None,
            "overhead_minutes_observed_count": len(overhead),
            "mean_pact_overhead_minutes": (
                statistics.fmean(overhead) if overhead else None
            ),
        }

    return {
        "record_count": len(records),
        "by_mode": summary,
        "interpretation_note": (
            "Directional pilot evidence only. Compare similar task/risk groups and do not collapse dimensions into one score."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate/summarize PACT pilot evaluation records")
    parser.add_argument("records", nargs="+")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    records = []
    failures = []

    for raw in args.records:
        path = pathlib.Path(raw)
        if not path.is_absolute():
            path = ROOT / path
        try:
            record = load(path)
        except Exception as exc:
            failures.append(f"{raw}: cannot read record: {exc}")
            continue

        errors = validate(record)
        if errors:
            failures.extend(f"{raw}: {error}" for error in errors)
            continue

        records.append(record)

    if failures:
        print("PACT eval: invalid record(s)", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 2

    if args.summary:
        result = aggregate(records)
    else:
        result = {
            "valid": True,
            "record_count": len(records),
            "task_ids": [record["task_id"] for record in records],
        }

    if args.json or args.summary:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"PACT eval: {len(records)} valid record(s)")
        for record in records:
            print(f"- {record['task_id']} ({record['mode']}, {record['risk_level']})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
