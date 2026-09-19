#!/usr/bin/env python3
"""Build a risk-adaptive candidate PACT Task Context Envelope."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

from risk import profile
from schema_validate import load_schema, validate_instance
from runtime_exec import runtime_command


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = ROOT / ".pact" / "schema" / "context-envelope.schema.json"
SELECTION_STRATEGY = "authority-aware-soft-token-budget-v1"
TOKEN_ESTIMATION_STRATEGY = "utf8-bytes-div-4"


def run_discovery(
    queries: list[str],
    knowledge_limit: int,
    *,
    code: bool,
    code_limit: int,
) -> dict:
    command = runtime_command(
        "discover",
        queries[0],
        "--limit",
        str(knowledge_limit),
        "--json",
    )
    for query in queries[1:]:
        command.extend(["--query", query])
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
    # discover --json returns 0 even for an empty result set. Any nonzero
    # status therefore represents an execution/indexing failure and must not
    # be downgraded to "no matches".
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "discovery failed")
    if not result.stdout.strip():
        return {
            "query": queries[0],
            "queries": queries,
            "result_count": 0,
            "results": [],
            "code_result_count": 0,
            "code_results": [],
        }
    return json.loads(result.stdout)


def validate(envelope: dict) -> list[str]:
    return validate_instance(envelope, load_schema(SCHEMA))


def extend_candidate_pool(primary: list[dict], wider: list[dict]) -> list[dict]:
    """Preserve canonical retrieval order; append wider-pool fallbacks only."""
    merged: list[dict] = []
    seen: set[str] = set()

    for tier, items in enumerate((primary, wider)):
        for ordinal, original in enumerate(items):
            path = str(original.get("path") or "")
            if not path or path in seen:
                continue
            seen.add(path)
            item = dict(original)
            item["_pool_tier"] = tier
            item["_pool_ordinal"] = ordinal
            merged.append(item)

    return merged


def repo_file(relative: str) -> pathlib.Path | None:
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError:
        return None
    return path if path.is_file() else None


def artifact_sha256(relative: str) -> str | None:
    path = repo_file(relative)
    if path is None:
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def estimated_file_tokens(relative: str) -> int:
    """Estimate downstream read cost without materializing file contents."""
    path = repo_file(relative)
    if path is None:
        return 1
    try:
        size = path.stat().st_size
    except OSError:
        return 1
    return max((int(size) + 3) // 4, 1)


def knowledge_priority(item: dict) -> tuple[int, bool]:
    """Preserve retrieval ranking; authority only affects soft-budget treatment."""
    typ = item.get("artifact_type")
    status = item.get("status")
    mandatory = (
        (typ == "rule" and status == "confirmed")
        or (typ == "decision" and status == "implemented")
    )
    return int(item.get("score", 0)), mandatory


def code_priority(item: dict) -> int:
    """Use the retrieval/fusion score as the canonical code ranking."""
    return int(item.get("score", 0))


def select_context_candidates(
    knowledge: list[dict],
    code: list[dict],
    *,
    token_budget: int,
    knowledge_limit: int,
    code_limit: int,
) -> tuple[list[dict], list[dict], dict]:
    candidates: list[dict] = []
    candidate_tokens = 0

    for ordinal, original in enumerate(knowledge):
        item = dict(original)
        estimated = estimated_file_tokens(str(item.get("path", "")))
        item["estimated_tokens"] = estimated
        priority, mandatory = knowledge_priority(item)
        candidate_tokens += estimated
        candidates.append({
            "kind": "knowledge",
            "item": item,
            "estimated_tokens": estimated,
            "priority": priority,
            "mandatory": mandatory,
            "pool_tier": int(item.get("_pool_tier", 0)),
            "ordinal": int(item.get("_pool_ordinal", ordinal)),
        })

    for ordinal, original in enumerate(code):
        item = dict(original)
        estimated = estimated_file_tokens(str(item.get("path", "")))
        item["estimated_tokens"] = estimated
        candidate_tokens += estimated
        candidates.append({
            "kind": "code",
            "item": item,
            "estimated_tokens": estimated,
            "priority": code_priority(item),
            "mandatory": False,
            "pool_tier": int(item.get("_pool_tier", 0)),
            "ordinal": int(item.get("_pool_ordinal", ordinal)),
        })

    candidates.sort(
        key=lambda candidate: (
            -int(candidate["mandatory"]),
            candidate["pool_tier"],
            candidate["ordinal"],
            0 if candidate["kind"] == "knowledge" else 1,
            candidate["item"].get("path", ""),
        )
    )

    selected_knowledge: list[dict] = []
    selected_code: list[dict] = []
    used_tokens = 0
    dropped_token = 0
    dropped_count = 0
    authority_candidates_dropped = 0

    for candidate in candidates:
        kind = candidate["kind"]
        item = candidate["item"]
        estimated = candidate["estimated_tokens"]
        mandatory = candidate["mandatory"]

        if kind == "knowledge" and len(selected_knowledge) >= knowledge_limit:
            dropped_count += 1
            authority_candidates_dropped += int(mandatory)
            continue
        if kind == "code" and len(selected_code) >= code_limit:
            dropped_count += 1
            continue

        fits_budget = (
            token_budget == 0
            or used_tokens + estimated <= token_budget
        )
        if not fits_budget and not mandatory:
            dropped_token += 1
            continue

        if kind == "knowledge":
            selected_knowledge.append(item)
        else:
            selected_code.append(item)
        used_tokens += estimated

    dropped_total = dropped_token + dropped_count
    budget = {
        "limit_tokens": token_budget,
        "selected_estimated_tokens": used_tokens,
        "candidate_estimated_tokens": candidate_tokens,
        "knowledge_selected": len(selected_knowledge),
        "code_selected": len(selected_code),
        "dropped_candidates": dropped_total,
        "dropped_for_token_budget": dropped_token,
        "dropped_for_count_limit": dropped_count,
        "authority_candidates_dropped": authority_candidates_dropped,
        "truncated": dropped_total > 0,
        "authority_overage_tokens": (
            max(used_tokens - token_budget, 0)
            if token_budget > 0
            else 0
        ),
        "selection_strategy": SELECTION_STRATEGY,
        "token_estimation": TOKEN_ESTIMATION_STRATEGY,
    }
    return selected_knowledge, selected_code, budget


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a candidate PACT task context")
    parser.add_argument("task")
    parser.add_argument("--goal")
    parser.add_argument("--success", required=True, help="observable success condition")
    parser.add_argument("--risk", choices=["low", "medium", "high"], default="medium")
    parser.add_argument(
        "--query",
        dest="queries",
        action="append",
        default=[],
        help="discovery query; repeat for multi-query fusion (defaults to task)",
    )
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
        help="override soft estimated materialization token budget; 0 disables it",
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
    queries = args.queries or [args.task]
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

    # Preserve the normal retrieval result as the canonical ranked prefix.
    # A second, wider query only supplies fallback candidates when token
    # budgeting skips a canonical large file.
    knowledge_pool_limit = max(knowledge_limit * 3, knowledge_limit + 8)
    code_pool_limit = max(code_limit * 3, code_limit + 8)

    try:
        discovery = run_discovery(
            queries,
            knowledge_limit,
            code=code_enabled,
            code_limit=code_limit,
        )
        wider_discovery = run_discovery(
            queries,
            knowledge_pool_limit,
            code=code_enabled,
            code_limit=code_pool_limit,
        )
    except Exception as exc:
        print(f"PACT context: discovery failed: {exc}", file=sys.stderr)
        return 2

    queries = discovery.get("queries", queries)
    candidate_results = extend_candidate_pool(
        discovery.get("results", []),
        wider_discovery.get("results", []),
    )
    candidate_code_results = extend_candidate_pool(
        discovery.get("code_results", []),
        wider_discovery.get("code_results", []),
    )
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
            f"Context budgets omitted {budget['dropped_candidates']} lower-priority "
            "candidate(s); increase --token-budget/--limit/--code-limit if they "
            "could materially change the task."
        )
    if budget["authority_candidates_dropped"]:
        unknowns.append(
            f"{budget['authority_candidates_dropped']} authority candidate(s) "
            "were omitted only because the hard knowledge-count limit was reached; "
            "increase --limit before claiming context sufficiency."
        )
    if budget["authority_overage_tokens"]:
        unknowns.append(
            "Authoritative Product Rule/Decision context exceeded the soft token "
            f"budget by {budget['authority_overage_tokens']} estimated token(s); "
            "authority was preserved and the overage is explicit."
        )

    if args.risk == "high":
        if not architecture:
            if candidate_architecture:
                unknowns.append(
                    "High-risk task: relevant Architecture candidates were not "
                    "selected under current context budgets; expand context."
                )
            else:
                unknowns.append(
                    "High-risk task: no matching current Architecture artifact was "
                    "discovered; inspect architecture/contracts manually."
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
            "High-risk task: inspect relevant public contracts/schema and Git history "
            "when the change can affect them."
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
        "discovery_query": queries[0],
        "discovery_queries": queries,
        "domains": domains,
        "artifacts": [
            {
                "path": item["path"],
                "id": item.get("id"),
                "artifact_type": item["artifact_type"],
                "title": item["title"],
                "score": item["score"],
                "reasons": item.get("reasons", []),
                "sha256": artifact_sha256(item["path"]),
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
