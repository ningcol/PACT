#!/usr/bin/env python3
"""Build a risk-adaptive, authority-aware candidate PACT Task Context Envelope."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

from risk import profile
from schema_validate import load_schema, validate_instance


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = ROOT / ".pact" / "schema" / "context-envelope.schema.json"
SELECTION_STRATEGY = "authority-aware-soft-budget-v1"


def run_discovery(
    query: str,
    knowledge_limit: int,
    *,
    code: bool,
    code_limit: int,
) -> dict:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pact" / "discover.py"),
        query,
        "--limit",
        str(knowledge_limit),
        "--json",
    ]
    if code:
        command.extend([
            "--code",
            "--code-limit",
            str(code_limit),
        ])

    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode not in {0, 1}:
        raise RuntimeError(result.stderr.strip() or "discovery failed")
    if not result.stdout.strip():
        return {
            "query": query,
            "result_count": 0,
            "results": [],
            "code_result_count": 0,
            "code_results": [],
        }
    return json.loads(result.stdout)


def validate(envelope: dict) -> list[str]:
    return validate_instance(envelope, load_schema(SCHEMA))


def knowledge_priority(item: dict) -> tuple[int, bool]:
    typ = item.get("artifact_type")
    status = item.get("status")
    bonus = 0
    mandatory = False

    if typ == "rule" and status == "confirmed":
        bonus += 140
        mandatory = True
    elif typ == "decision" and status == "implemented":
        bonus += 120
        mandatory = True
    elif typ == "domain" and status == "confirmed":
        bonus += 80
    elif typ == "architecture" or str(item.get("path", "")).startswith(
        "docs/architecture/"
    ):
        bonus += 70
    elif typ == "drift" and status == "known":
        bonus += 65
    elif typ == "change" and status == "active":
        bonus += 35

    return int(item.get("score", 0)) + bonus, mandatory


def code_priority(item: dict) -> int:
    score = int(item.get("score", 0))
    if item.get("relation") == "direct-match":
        score += 35
    if item.get("is_test"):
        score += 15
    score += {
        "direct": 15,
        "relative-resolved": 10,
        "ast-resolved": 8,
        "heuristic": 0,
    }.get(item.get("confidence"), 0)
    return score


def select_context_candidates(
    knowledge: list[dict],
    code: list[dict],
    *,
    token_budget: int,
    knowledge_limit: int,
    code_limit: int,
) -> tuple[list[dict], list[dict], dict]:
    candidates = []
    candidate_tokens = 0

    for item in knowledge:
        estimated = max(int(item.get("estimated_tokens", 1)), 1)
        priority, mandatory = knowledge_priority(item)
        candidate_tokens += estimated
        candidates.append({
            "kind": "knowledge",
            "item": item,
            "estimated_tokens": estimated,
            "priority": priority,
            "mandatory": mandatory,
        })

    for item in code:
        estimated = max(int(item.get("estimated_tokens", 1)), 1)
        candidate_tokens += estimated
        candidates.append({
            "kind": "code",
            "item": item,
            "estimated_tokens": estimated,
            "priority": code_priority(item),
            "mandatory": False,
        })

    candidates.sort(
        key=lambda candidate: (
            -int(candidate["mandatory"]),
            -candidate["priority"],
            candidate["estimated_tokens"],
            candidate["item"].get("path", ""),
        )
    )

    selected_knowledge: list[dict] = []
    selected_code: list[dict] = []
    used_tokens = 0
    dropped = 0
    dropped_authority = 0

    for candidate in candidates:
        kind = candidate["kind"]
        item = candidate["item"]
        estimated = candidate["estimated_tokens"]
        mandatory = candidate["mandatory"]

        if kind == "knowledge" and len(selected_knowledge) >= knowledge_limit:
            dropped += 1
            dropped_authority += int(mandatory)
            continue
        if kind == "code" and len(selected_code) >= code_limit:
            dropped += 1
            continue

        fits_budget = (
            token_budget == 0
            or used_tokens + estimated <= token_budget
        )

        # Confirmed Product Rules and implemented Decisions are authority evidence.
        # The budget is soft for these items; any overage is reported explicitly.
        if not fits_budget and not mandatory:
            dropped += 1
            continue

        if kind == "knowledge":
            selected_knowledge.append(item)
        else:
            selected_code.append(item)
        used_tokens += estimated

    if not selected_knowledge and not selected_code and candidates:
        # A tiny caller-supplied budget must not silently produce zero context.
        top = candidates[0]
        if top["kind"] == "knowledge":
            selected_knowledge.append(top["item"])
        else:
            selected_code.append(top["item"])
        used_tokens += top["estimated_tokens"]
        dropped = max(dropped - 1, 0)

    budget = {
        "limit_tokens": token_budget,
        "selected_estimated_tokens": used_tokens,
        "candidate_estimated_tokens": candidate_tokens,
        "knowledge_selected": len(selected_knowledge),
        "code_selected": len(selected_code),
        "dropped_candidates": dropped,
        "authority_candidates_dropped": dropped_authority,
        "truncated": dropped > 0,
        "authority_overage_tokens": (
            max(used_tokens - token_budget, 0)
            if token_budget > 0
            else 0
        ),
        "selection_strategy": SELECTION_STRATEGY,
    }
    return selected_knowledge, selected_code, budget


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a candidate PACT task context")
    parser.add_argument("task")
    parser.add_argument("--goal")
    parser.add_argument("--success", required=True, help="observable success condition")
    parser.add_argument("--risk", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--query", help="discovery query; defaults to task")
    parser.add_argument(
        "--limit",
        type=int,
        help="override risk-profile selected knowledge artifact limit",
    )
    parser.add_argument(
        "--code-limit",
        type=int,
        help="override risk-profile selected code artifact limit",
    )
    parser.add_argument(
        "--token-budget",
        type=int,
        help=(
            "override soft estimated materialization token budget; "
            "0 disables token budgeting"
        ),
    )
    code_group = parser.add_mutually_exclusive_group()
    code_group.add_argument(
        "--code",
        dest="code",
        action="store_true",
        help="force code-aware context",
    )
    code_group.add_argument(
        "--no-code",
        dest="code",
        action="store_false",
        help="disable code-aware context even if the risk profile normally enables it",
    )
    parser.set_defaults(code=None)
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.token_budget is not None and args.token_budget < 0:
        parser.error("--token-budget must be >= 0")

    goal = args.goal or args.task
    query = args.query or args.task
    risk = profile(args.risk)

    knowledge_limit = max(args.limit or risk["knowledge_limit"], 1)
    code_limit = max(args.code_limit or risk["code_limit"], 1)
    token_budget = (
        risk["materialization_token_budget"]
        if args.token_budget is None
        else args.token_budget
    )
    code_enabled = (
        risk["code_context_default"]
        if args.code is None
        else bool(args.code)
    )

    # Fetch a wider candidate pool than we expect to select so a single huge or
    # low-value match does not starve later higher-value candidates.
    knowledge_pool_limit = max(knowledge_limit * 3, knowledge_limit + 8)
    code_pool_limit = max(code_limit * 3, code_limit + 8)

    try:
        discovery = run_discovery(
            query,
            knowledge_pool_limit,
            code=code_enabled,
            code_limit=code_pool_limit,
        )
    except Exception as exc:
        print(f"PACT context: discovery failed: {exc}", file=sys.stderr)
        return 2

    candidate_results = discovery.get("results", [])
    candidate_code_results = discovery.get("code_results", [])

    results, code_results, budget = select_context_candidates(
        candidate_results,
        candidate_code_results,
        token_budget=token_budget,
        knowledge_limit=knowledge_limit,
        code_limit=code_limit,
    )

    domains = sorted({
        domain
        for result in results
        for domain in result.get("domains", [])
    })

    rules = sorted({
        result["id"] or result["path"]
        for result in results
        if result.get("artifact_type") == "rule"
        and result.get("status") == "confirmed"
    })
    decisions = sorted({
        result["id"] or result["path"]
        for result in results
        if result.get("artifact_type") == "decision"
        and result.get("status") == "implemented"
    })
    verification = sorted({
        target
        for result in results
        for target in result.get("verification", [])
    })
    architecture = [
        result
        for result in results
        if result.get("artifact_type") == "architecture"
        or str(result.get("path", "")).startswith("docs/architecture/")
    ]

    candidate_architecture = [
        result
        for result in candidate_results
        if result.get("artifact_type") == "architecture"
        or str(result.get("path", "")).startswith("docs/architecture/")
    ]
    candidate_decisions = [
        result
        for result in candidate_results
        if result.get("artifact_type") == "decision"
        and result.get("status") == "implemented"
    ]

    unknowns: list[str] = []
    if not candidate_results:
        unknowns.append(
            "Project Discovery found no matching knowledge artifact; expand search semantically."
        )
    if not rules:
        unknowns.append(
            "No confirmed Product Rule was selected; candidate rules must not be treated as normative truth."
        )
    if code_enabled and not code_results:
        unknowns.append(
            "Code-aware discovery selected no matching code artifact; expand with project-specific code analysis if needed."
        )

    if budget["truncated"]:
        unknowns.append(
            f"Context soft budget/limits omitted {budget['dropped_candidates']} "
            "lower-priority candidate(s); increase --token-budget/--limit if "
            "they could materially change the task."
        )
    if budget["authority_candidates_dropped"]:
        unknowns.append(
            f"{budget['authority_candidates_dropped']} authority candidate(s) "
            "were omitted by the selected knowledge-count limit; increase "
            "--limit before claiming context sufficiency."
        )

    if args.risk == "high":
        if not architecture:
            if candidate_architecture:
                unknowns.append(
                    "High-risk task: relevant Architecture candidates were not "
                    "selected under current context limits/budget; expand context."
                )
            else:
                unknowns.append(
                    "High-risk task: no matching current Architecture artifact "
                    "was discovered; inspect architecture/contracts manually."
                )
        if not decisions:
            if candidate_decisions:
                unknowns.append(
                    "High-risk task: implemented Decision candidates were not "
                    "selected under current context limits; expand context."
                )
            else:
                unknowns.append(
                    "High-risk task: no implemented Decision Record was discovered; "
                    "inspect Decision/Git history when rationale matters."
                )
        unknowns.append(
            "High-risk task: inspect relevant public contracts/schema and Git "
            "history when the change can affect them."
        )

    envelope = {
        "version": 1,
        "status": "candidate",
        "task": args.task,
        "goal": goal,
        "observable_success": args.success,
        "risk_level": args.risk,
        "risk_policy": {
            "knowledge_limit": knowledge_limit,
            "code_context": code_enabled,
            "code_limit": code_limit,
            "materialization_token_budget": token_budget,
            "completion": risk["completion"],
        },
        "context_budget": budget,
        "discovery_query": query,
        "domains": domains,
        "artifacts": [
            {
                "path": item["path"],
                "id": item.get("id"),
                "artifact_type": item["artifact_type"],
                "title": item["title"],
                "score": item["score"],
                "reasons": item.get("reasons", []),
                "estimated_tokens": item["estimated_tokens"],
            }
            for item in results
        ],
        "code_artifacts": [
            {
                "path": item["path"],
                "language": item["language"],
                "is_test": item["is_test"],
                "symbols": item.get("symbols", []),
                "score": item["score"],
                "reasons": item.get("reasons", []),
                "relation": item.get("relation", "direct-match"),
                "confidence": item.get("confidence", "heuristic"),
                "estimated_tokens": item["estimated_tokens"],
            }
            for item in code_results
        ],
        "applicable_rules": rules,
        "decisions": decisions,
        "verification_targets": verification,
        "known_unknowns": unknowns,
    }

    errors = validate(envelope)
    if errors:
        print("PACT context: generated invalid envelope", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    rendered = json.dumps(envelope, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        path = pathlib.Path(args.output)
        if not path.is_absolute():
            path = ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
        print(f"PACT context: candidate envelope -> {path}")
    else:
        print(rendered, end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
