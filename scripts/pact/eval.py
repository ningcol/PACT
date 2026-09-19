#!/usr/bin/env python3
"""Validate/summarize pilot records and derive machine-observed task metrics."""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys
from collections import defaultdict

from schema_validate import load_schema, validate_instance
from protocol_ids import validate_task_id, confined_child
from task_contract import acceptance_review


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = ROOT / ".pact" / "schema" / "pilot-evaluation.schema.json"
OBSERVATION_SCHEMA = ROOT / ".pact" / "schema" / "task-observation.schema.json"


def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional(path: pathlib.Path) -> dict | None:
    if not path.is_file():
        return None
    return load(path)


def read_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.is_file():
        return []

    items: list[dict] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"invalid JSONL at {path}:{line_number}: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise ValueError(
                f"invalid JSONL object at {path}:{line_number}"
            )
        items.append(value)
    return items


def validate(record: dict) -> list[str]:
    return validate_instance(record, load_schema(SCHEMA))


def validate_observation(record: dict) -> list[str]:
    return validate_instance(record, load_schema(OBSERVATION_SCHEMA))


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


def nullable_mean(values: list[int | float | None]) -> float | None:
    observed = [float(value) for value in values if value is not None]
    return statistics.fmean(observed) if observed else None


def summarize_observations(observations: list[dict]) -> dict:
    def summarize(items: list[dict]) -> dict:
        token_values = [
            item["context"]["selected_estimated_tokens"]
            for item in items
        ]
        token_budgets = [
            item["context"]["token_budget"]
            for item in items
        ]
        changed_values = [
            item["task_change"]["changed_files"]
            for item in items
        ]
        return {
            "task_count": len(items),
            "completed": sum(
                item["completion"]["final_complete"] for item in items
            ),
            "verification_runs": sum(
                item["runs"]["total"] for item in items
            ),
            "verification_run_failures": sum(
                item["runs"]["failed"] for item in items
            ),
            "completion_attempts": sum(
                item["completion"]["attempts"] for item in items
            ),
            "failed_completion_attempts": sum(
                item["completion"]["failed_attempts"] for item in items
            ),
            "trust_blocks": {
                "stale_workspace": sum(
                    item["completion"]["stale_workspace_blocks"]
                    for item in items
                ),
                "stale_task_contract": sum(
                    item["completion"]["stale_contract_blocks"]
                    for item in items
                ),
                "acceptance_gap": sum(
                    item["completion"]["acceptance_gap_blocks"]
                    for item in items
                ),
                "convergence_coverage": sum(
                    item["completion"]["convergence_coverage_blocks"]
                    for item in items
                ),
                "change_coverage": sum(
                    item["completion"]["change_coverage_blocks"]
                    for item in items
                ),
                "ci_requirement": sum(
                    item["completion"]["ci_requirement_blocks"]
                    for item in items
                ),
            },
            "mean_knowledge_artifacts": (
                statistics.fmean(
                    item["context"]["knowledge_artifacts"]
                    for item in items
                )
                if items
                else None
            ),
            "mean_code_artifacts": (
                statistics.fmean(
                    item["context"]["code_artifacts"]
                    for item in items
                )
                if items
                else None
            ),
            "token_observed_tasks": sum(
                value is not None for value in token_values
            ),
            "mean_selected_estimated_tokens": nullable_mean(token_values),
            "mean_token_budget": nullable_mean(token_budgets),
            "context_truncated_tasks": sum(
                (
                    item["context"]["dropped_candidates"] or 0
                ) > 0
                for item in items
            ),
            "task_change_observed_tasks": sum(
                value is not None for value in changed_values
            ),
            "total_changed_files": sum(
                int(value)
                for value in changed_values
                if value is not None
            ),
            "mean_changed_files": nullable_mean(changed_values),
            "final_impact_tasks": sum(
                item["task_change"]["final_impact"] is True
                for item in items
            ),
        }

    by_risk = {}
    for risk in ("low", "medium", "high"):
        items = [
            item for item in observations
            if item.get("risk_level") == risk
        ]
        if items:
            by_risk[risk] = summarize(items)

    return {
        "task_count": len(observations),
        "overall": summarize(observations),
        "by_risk": by_risk,
        "interpretation_note": (
            "Machine-observed operational/trust metrics only. Human owner "
            "interactions, comprehension, subjective overload, and overhead "
            "remain separate observations; do not collapse these dimensions "
            "into one score."
        ),
    }


def discover_task_ids() -> list[str]:
    task_root = ROOT / ".pact" / "tasks"
    if not task_root.is_dir():
        return []
    return sorted(
        path.name
        for path in task_root.iterdir()
        if path.is_dir() and (path / "task.json").is_file()
    )


def blocker_count(
    attempts: list[dict],
    code: str,
    *legacy_needles: str,
) -> int:
    count = 0
    for attempt in attempts:
        blockers = attempt.get("blockers")
        if isinstance(blockers, list) and code in blockers:
            count += 1
            continue
        text = "\n".join(str(value) for value in attempt.get("errors", []))
        if any(needle in text for needle in legacy_needles):
            count += 1
    return count


def run_receipts(task_id: str, evidence: dict | None) -> list[dict]:
    paths: set[pathlib.Path] = set()
    root = ROOT / ".pact" / "runs" / task_id
    if root.is_dir():
        paths.update(root.rglob("*.json"))

    if evidence:
        for claim in evidence.get("claims", []):
            for item in claim.get("evidence", []):
                if item.get("provenance") != "pact-run":
                    continue
                ref = item.get("ref")
                if not isinstance(ref, str) or not ref:
                    continue
                path = pathlib.Path(ref).expanduser()
                paths.add(path if path.is_absolute() else ROOT / path)

    receipts: list[dict] = []
    seen: set[pathlib.Path] = set()
    for path in sorted(paths):
        resolved = path.resolve()
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)
        item = load_optional(resolved)
        if item and item.get("task_id") == task_id and "status" in item:
            receipts.append(item)
    return receipts


def derive_task(task_id: str) -> dict:
    validate_task_id(task_id)
    task_dir = confined_child(ROOT / ".pact" / "tasks", task_id)
    manifest = load_optional(task_dir / "task.json")
    if manifest is None:
        raise FileNotFoundError(f"task manifest not found for {task_id}")

    contract_path = manifest.get("contract")
    contract = (
        load_optional(ROOT / contract_path)
        if isinstance(contract_path, str)
        else None
    )
    context_path = manifest.get("context")
    context = (
        load_optional(ROOT / context_path)
        if isinstance(context_path, str)
        else None
    )

    bundle = ROOT / manifest.get(
        "completion_bundle",
        f".pact/completions/{task_id}",
    )
    evidence = load_optional(bundle / "evidence.json")
    convergence = load_optional(bundle / "convergence.json")
    owner = load_optional(bundle / "owner-report.json")

    criteria = contract.get("acceptance_criteria", []) if contract else []
    acceptance = {
        "total": len(criteria),
        "outcomes": sum(item.get("kind") == "outcome" for item in criteria),
        "constraints": sum(item.get("kind") == "constraint" for item in criteria),
        "evidence_verified": 0,
        "owner_report_covered": 0,
        "unverified": [item.get("id") for item in criteria],
        "owner_report_missing": [],
    }
    if contract and evidence and owner:
        _, coverage = acceptance_review(contract, evidence, owner)
        acceptance = {
            **coverage,
            "outcomes": sum(item.get("kind") == "outcome" for item in criteria),
            "constraints": sum(item.get("kind") == "constraint" for item in criteria),
        }

    attempts = read_jsonl(task_dir / "completion-attempts.jsonl")
    receipts = run_receipts(task_id, evidence)

    claims = evidence.get("claims", []) if evidence else []
    findings = convergence.get("findings", []) if convergence else []

    context_budget = (
        context.get("context_budget", {})
        if isinstance(context, dict)
        else {}
    )
    risk_policy = (
        context.get("risk_policy", {})
        if isinstance(context, dict)
        else {}
    )

    raw_task_change = manifest.get("task_change")
    if isinstance(raw_task_change, dict):
        task_change_supported = bool(raw_task_change.get("supported"))
        if task_change_supported:
            task_change_paths = list(raw_task_change.get("changed_files", []))
            task_change = {
                "supported": True,
                "changed_files": len(task_change_paths),
                "paths": task_change_paths,
                "final_impact": bool(
                    manifest.get("final_impact")
                    and (ROOT / manifest["final_impact"]).is_file()
                ),
                "reason": None,
            }
        else:
            task_change = {
                "supported": False,
                "changed_files": None,
                "paths": None,
                "final_impact": None,
                "reason": str(
                    raw_task_change.get("reason")
                    or "exact task changed-file attribution unavailable"
                ),
            }
    else:
        task_change = {
            "supported": False,
            "changed_files": None,
            "paths": None,
            "final_impact": None,
            "reason": "task changed-file attribution has not been observed yet",
        }

    observation = {
        "version": 1,
        "task_id": task_id,
        "task_status": manifest.get("status", "unknown"),
        "risk_level": manifest.get("risk_level", "medium"),
        "acceptance": acceptance,
        "context": {
            "knowledge_artifacts": len(context.get("artifacts", [])) if context else 0,
            "code_artifacts": len(context.get("code_artifacts", [])) if context else 0,
            "known_unknowns": len(context.get("known_unknowns", [])) if context else 0,
            "token_budget": (
                context_budget.get("limit_tokens")
                if context_budget
                else risk_policy.get("materialization_token_budget")
            ),
            "selected_estimated_tokens": context_budget.get(
                "selected_estimated_tokens"
            ),
            "candidate_estimated_tokens": context_budget.get(
                "candidate_estimated_tokens"
            ),
            "dropped_candidates": context_budget.get("dropped_candidates"),
            "authority_overage_tokens": context_budget.get(
                "authority_overage_tokens"
            ),
        },
        "runs": {
            "total": len(receipts),
            "passed": sum(item.get("status") == "pass" for item in receipts),
            "failed": sum(item.get("status") == "fail" for item in receipts),
            "workspace_changed": sum(
                bool(item.get("workspace_changed")) for item in receipts
            ),
        },
        "completion": {
            "attempts": len(attempts),
            "failed_attempts": sum(not bool(item.get("complete")) for item in attempts),
            "stale_workspace_blocks": blocker_count(
                attempts,
                "stale-workspace",
                "stale pact-run receipt",
                "verified workspace",
            ),
            "stale_contract_blocks": blocker_count(
                attempts,
                "stale-task-contract",
                "task_contract_sha256",
            ),
            "acceptance_gap_blocks": blocker_count(
                attempts,
                "acceptance-gap",
                "acceptance criterion",
                "Owner Report acceptance",
            ),
            "convergence_coverage_blocks": blocker_count(
                attempts,
                "convergence-coverage",
                "convergence coverage:",
            ),
            "change_coverage_blocks": blocker_count(
                attempts,
                "change-coverage",
                "change coverage:",
                "Task changed file missing",
            ),
            "ci_requirement_blocks": blocker_count(
                attempts,
                "ci-metadata-required",
                "CI-metadata Evidence",
            ),
            "final_complete": manifest.get("status") == "completed",
        },
        "task_change": task_change,
        "evidence": {
            "claims": len(claims),
            "passed": sum(item.get("status") == "pass" for item in claims),
            "failed": sum(item.get("status") == "fail" for item in claims),
            "unverified": sum(item.get("status") == "unverified" for item in claims),
        },
        "convergence": {
            "findings": len(findings),
            "owner_decisions": sum(
                item.get("classification") == "owner-decision"
                for item in findings
            ),
        },
        "owner_status": owner.get("status") if owner else None,
        "human_required": [
            "owner_interactions.product_decisions",
            "owner_interactions.technical_escalations",
            "owner_interactions.clarification_rounds",
            "owner_interactions.comprehension",
            "context_quality.overload_observed",
            "pact_overhead_minutes",
        ],
    }

    errors = validate_observation(observation)
    if errors:
        raise ValueError("invalid derived observation: " + "; ".join(errors))

    return observation


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate/summarize PACT pilot records or derive machine task observations"
    )
    parser.add_argument("records", nargs="*")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--task",
        help="derive machine-observed metrics from one prepared PACT task",
    )
    parser.add_argument(
        "--all-tasks",
        action="store_true",
        help="derive and summarize all local prepared task observations",
    )
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.all_tasks:
        if args.task or args.records or args.summary:
            parser.error(
                "--all-tasks cannot be combined with --task, record paths, "
                "or --summary"
            )

        observations = []
        failures = []
        for task_id in discover_task_ids():
            try:
                observations.append(derive_task(task_id))
            except Exception as exc:
                failures.append({
                    "task_id": task_id,
                    "error": str(exc),
                })

        result = {
            "summary": summarize_observations(observations),
            "observations": observations,
            "errors": failures,
        }
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            path = pathlib.Path(args.output)
            if not path.is_absolute():
                path = ROOT / path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered, encoding="utf-8")
            if not args.json:
                print(f"PACT eval machine summary: {path}")
        if args.json or not args.output:
            print(rendered, end="")
        return 0

    if args.task:
        if args.records or args.summary or args.all_tasks:
            parser.error("--task cannot be combined with record paths, --summary, or --all-tasks")
        try:
            result = derive_task(args.task)
        except Exception as exc:
            print(f"PACT eval: cannot derive task observation: {exc}", file=sys.stderr)
            return 2

        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            path = pathlib.Path(args.output)
            if not path.is_absolute():
                path = ROOT / path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered, encoding="utf-8")
            if not args.json:
                print(f"PACT eval observation: {path}")
        if args.json or not args.output:
            print(rendered, end="")
        return 0

    if not args.records:
        parser.error(
            "provide evaluation record(s), --task TASK-ID, or --all-tasks"
        )

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
