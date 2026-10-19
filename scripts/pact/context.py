#!/usr/bin/env python3
"""Build a risk-adaptive candidate PACT Task Context Envelope."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys

from repository_files import DEFAULT_PRUNE_DIRS

from risk import profile
from schema_validate import load_schema, validate_instance
from scope_routing import route_only
from discover import exact_match_priority
from runtime_exec import runtime_command


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = ROOT / ".pact" / "schema" / "context-envelope.schema.json"
SELECTION_STRATEGY = "authority-aware-soft-token-budget-v1"
TOKEN_ESTIMATION_STRATEGY = "utf8-bytes-div-4"
CODE_CANDIDATE_HINT_LIMIT = 5
MODULE_README_HINT_LIMIT = 3
MODULE_README_CODE_CANDIDATES = 24
MODULE_README_SIZE_LIMIT = 128 * 1024
GOVERNANCE_PATHS = (
    "docs/governance/truth-ownership.md",
    "docs/governance/decision-authority.md",
    "docs/governance/completion-contract.md",
)
RULE_ID = re.compile(r"^RULE-[A-Z0-9]+(?:-[A-Z0-9]+)*$")


def run_discovery(
    queries: list[str],
    knowledge_limit: int,
    *,
    code: bool,
    code_limit: int,
    intent: str | None = None,
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
    if intent:
        command.extend(["--intent", intent])

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
        raise RuntimeError(
            "discover --json exited 0 without a response; "
            "refuse to infer that no Decision/Rule exists"
        )
    data = json.loads(result.stdout)
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("results"), list)
        or not isinstance(data.get("code_results"), list)
        or any(not isinstance(row, dict) for row in data["results"])
        or any(not isinstance(row, dict) for row in data["code_results"])
        or ("result_count" in data
            and data["result_count"] != len(data["results"]))
        or ("code_result_count" in data
            and data["code_result_count"] != len(data["code_results"]))
    ):
        raise RuntimeError(
            "discover --json returned malformed/inconsistent results; "
            "refuse to prepare an empty or partial Context"
        )
    return data


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


def preserves_task_as_primary(task: str, queries: list[str]) -> bool:
    """Whether explicit queries preserve the original task as primary intent."""
    return (
        len(queries) > 1
        and queries[0].strip().casefold() == task.strip().casefold()
    )


def compose_primary_preserving_pool(
    primary_selected: list[dict] | None,
    fused: list[dict],
    wider: list[dict],
) -> list[dict]:
    """Keep already-selected primary context canonical; append fused fallback."""
    fused_pool = extend_candidate_pool(fused, wider)
    if primary_selected is None:
        return fused_pool
    return extend_candidate_pool(primary_selected, fused_pool)


def build_code_candidate_hints(
    candidates: list[dict],
    selected_code: list[dict],
    *,
    limit: int = CODE_CANDIDATE_HINT_LIMIT,
) -> list[dict]:
    """Expose bounded fallback metadata without changing materialized Context."""
    if limit <= 0:
        return []

    selected_paths = {
        str(item.get("path") or "")
        for item in selected_code
        if item.get("path")
    }
    hints: list[dict] = []
    for item in candidates:
        if int(item.get("_pool_tier", 0)) <= 0:
            continue
        path = str(item.get("path") or "")
        if not path or path in selected_paths:
            continue

        hints.append({
            "path": path,
            "language": str(item.get("language") or "unknown"),
            "relation": str(item.get("relation") or "direct-match"),
            "confidence": str(item.get("confidence") or "heuristic"),
            "reasons": list(item.get("reasons", [])),
            "estimated_tokens": estimated_file_tokens(path),
        })
        if len(hints) >= limit:
            break

    return hints


def nearby_readme_hints(
    selected_code: list[dict],
    *,
    limit: int = MODULE_README_HINT_LIMIT,
    ancestor_limit: int = 4,
) -> list[str]:
    """Bounded metadata-only lookup adjacent to already selected code paths.

    No directory walk, content read or global README ranking. Git-ignored and
    symbolic paths cannot become trusted hints, even if search hits them.
    """
    if limit <= 0 or ancestor_limit <= 0:
        return []
    root = ROOT.resolve()
    found: set[str] = set()
    hints: list[str] = []
    # This stays bounded even if --code-limit is set extremely high.
    for code in selected_code[:MODULE_README_CODE_CANDIDATES]:
        raw = str(code.get("path") or "")
        pure = pathlib.PurePosixPath(raw)
        if not raw or pure.is_absolute() or ".." in pure.parts:
            continue
        parent = pure.parent
        for _ in range(ancestor_limit):
            if str(parent) in {".", ""}:
                break
            if any(part in DEFAULT_PRUNE_DIRS for part in parent.parts):
                break
            relative = (parent / "README.md").as_posix()
            if relative in found:
                parent = parent.parent
                continue
            candidate = ROOT / relative
            try:
                candidate.resolve().relative_to(root)
                if candidate.is_symlink() or not candidate.is_file():
                    parent = parent.parent
                    continue
                # Do not follow symlinked parent directories either.
                ancestor = candidate.parent
                if any(
                    component.is_symlink()
                    for component in (ancestor, *ancestor.parents)
                    if component != root and root in component.parents
                ):
                    parent = parent.parent
                    continue
                if candidate.stat().st_size > MODULE_README_SIZE_LIMIT:
                    parent = parent.parent
                    continue
                check = subprocess.run(
                    ["git", "check-ignore", "-q", "--", relative],
                    cwd=ROOT, capture_output=True, timeout=5, check=False,
                )
                if check.returncode == 0:
                    parent = parent.parent
                    continue
            except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
                parent = parent.parent
                continue
            found.add(relative)
            hints.append(
                f"Module README hint (metadata only): {relative}; "
                f"near selected code {raw}; not normative Product Truth"
            )
            if len(hints) >= limit:
                return hints
            parent = parent.parent
    return hints


def governance_path_hints() -> list[str]:
    """Compatibility-safe navigation text in the existing advisory field."""
    return [
        f"Governance navigation path (metadata only, not a business Rule): {path}"
        for path in GOVERNANCE_PATHS
        if repo_file(path) is not None
    ]


def required_rule_gaps(
    rule_ids: list[str],
    selected: list[dict],
    candidates: list[dict],
    exact: dict[str, dict | None],
) -> list[str]:
    """Explicit requirements fail closed; never infer mandatory IDs from prose."""
    selected_rules = set(applicable_rule_ids(selected))
    candidates_by_id = {
        str(item.get("id")): item
        for item in candidates
        if item.get("id")
    }
    errors: list[str] = []
    for rule_id in rule_ids:
        if rule_id in selected_rules:
            continue
        doc = candidates_by_id.get(rule_id) or exact.get(rule_id)
        if doc is None:
            reason = "absent (no artifact with that stable ID)"
        elif doc.get("artifact_type") != "rule":
            reason = "identifier belongs to a non-Rule artifact"
        elif doc.get("mixed_authority"):
            reason = "mixed confirmed/pending sections; not normative"
        elif doc.get("status") != "confirmed":
            reason = f"status {doc.get('status')!r} is not confirmed"
        else:
            reason = "confirmed, but not selected under current count/token budget"
        errors.append(
            f"required Rule {rule_id}: {reason}; inspect the artifact, "
            "increase --limit or supply a narrower --query, then retry"
        )
    return errors


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


def applicable_rule_ids(results: list[dict]) -> list[str]:
    """Promote only wholly confirmed rule artifacts to normative Context."""
    return sorted({
        result.get("id") or result["path"]
        for result in results
        if result.get("artifact_type") == "rule"
        and result.get("status") == "confirmed"
        and not result.get("mixed_authority")
    })


def knowledge_priority(item: dict) -> tuple[int, bool]:
    """Preserve retrieval ranking; authority only affects soft-budget treatment."""
    typ = item.get("artifact_type")
    status = item.get("status")
    mandatory = (
        (typ == "rule" and status == "confirmed" and not item.get("mixed_authority"))
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
    parser.add_argument("--intent", choices=["work", "decision", "history"], help="optional retrieval priority; default unchanged")
    parser.add_argument(
        "--scope-first", action="store_true",
        help="opt-in: route by project-declared Domain name/path before materializing weak Decision matches",
    )
    parser.add_argument("--require-rule", dest="required_rules", action="append", default=[], help="require a confirmed RULE-* artifact in selected Context")
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.token_budget is not None and args.token_budget < 0:
        parser.error("--token-budget must be >= 0")

    required_rules = list(dict.fromkeys(args.required_rules))
    if len(required_rules) > 8 or any(not RULE_ID.fullmatch(x) for x in required_rules):
        parser.error("--require-rule expects up to eight unique canonical RULE-* IDs")
    goal = args.goal or args.task
    queries = list(dict.fromkeys([*(args.queries or [args.task]), *required_rules]))
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

    preserve_primary = preserves_task_as_primary(args.task, queries)

    try:
        discovery = run_discovery(
            queries,
            knowledge_limit,
            code=code_enabled,
            code_limit=code_limit,
                intent=args.intent,
        )
        wider_discovery = run_discovery(
            queries,
            knowledge_pool_limit,
            code=code_enabled,
            code_limit=code_pool_limit,
                intent=args.intent,
        )

        primary_selected_results = None
        primary_selected_code_results = None
        if preserve_primary:
            primary_discovery = run_discovery(
                [queries[0]],
                knowledge_limit,
                code=code_enabled,
                code_limit=code_limit,
                intent=args.intent,
            )
            primary_wider_discovery = run_discovery(
                [queries[0]],
                knowledge_pool_limit,
                code=code_enabled,
                code_limit=code_pool_limit,
                intent=args.intent,
            )
            primary_candidate_results = extend_candidate_pool(
                primary_discovery.get("results", []),
                primary_wider_discovery.get("results", []),
            )
            primary_candidate_code_results = extend_candidate_pool(
                primary_discovery.get("code_results", []),
                primary_wider_discovery.get("code_results", []),
            )
            (
                primary_selected_results,
                primary_selected_code_results,
                _,
            ) = select_context_candidates(
                primary_candidate_results,
                primary_candidate_code_results,
                token_budget=token_budget,
                knowledge_limit=knowledge_limit,
                code_limit=code_limit,
            )
    except Exception as exc:
        print(f"PACT context: discovery failed: {exc}", file=sys.stderr)
        return 2

    queries = discovery.get("queries", queries)
    candidate_results = compose_primary_preserving_pool(
        primary_selected_results,
        discovery.get("results", []),
        wider_discovery.get("results", []),
    )
    candidate_code_results = compose_primary_preserving_pool(
        primary_selected_code_results,
        discovery.get("code_results", []),
        wider_discovery.get("code_results", []),
    )

    scope_route = None
    scope_source_hashes: dict[str, str] = {}
    if args.scope_first:
        try:
            scope_route = route_only(args.task, ROOT)
        except (ValueError, OSError, RuntimeError) as exc:
            print(f"PACT context: cannot verify Domain source map: {exc}", file=sys.stderr)
            return 2

        # Pin BOTH the routed Domain landing page and displayed authority
        # candidates to the same verified Markdown generation. The capped
        # hidden candidate set is not materialized and cannot authorize a
        # successful scoped finish when it overflows.
        source_paths = {
            item["path"] for item in scope_route["candidates"]
        } | {item["path"] for item in scope_route["domains"]}
        for relative in sorted(source_paths):
            digest = artifact_sha256(relative)
            if digest is None:
                print(
                    "PACT context: routed Domain/authority source is missing: "
                    + repr(relative), file=sys.stderr,
                )
                return 2
            scope_source_hashes[relative] = digest
        for item in scope_route["candidates"]:
            item["sha256"] = scope_source_hashes[item["path"]]

        # Do not mix cached/source metadata from generation N with a source
        # digest from generation N+1 if a concurrent writer intervened between
        # route resolution and hashing. Reverify every authority source and
        # mapping against the current source fingerprint, then confirm the
        # digests we just attached still identify those same bytes.
        try:
            fresh = route_only(args.task, ROOT)
            original_metadata = {
                key: value for key, value in scope_route.items()
                if key != "candidates"
            }
            fresh_metadata = {
                key: value for key, value in fresh.items()
                if key != "candidates"
            }
            recorded = [
                {key: val for key, val in row.items() if key != "sha256"}
                for row in scope_route["candidates"]
            ]
            if original_metadata != fresh_metadata or recorded != fresh["candidates"]:
                raise ValueError("Domain scope changed while source digests were captured")
            if any(
                artifact_sha256(relative) != digest
                for relative, digest in scope_source_hashes.items()
            ):
                raise ValueError("Domain scope source bytes changed while being verified")
        except (ValueError, OSError, RuntimeError) as exc:
            print(f"PACT context: inconsistent Domain source snapshot: {exc}",
                  file=sys.stderr)
            return 2

        # The full source-linked ID/path set must not be truncated by the
        # 12-item *presentation* cap; it never enters Context JSON.
        all_candidate_paths = set(scope_route.pop("_all_candidate_paths"))

        # This is an EXPLICITLY OPT-IN materialization policy, never an
        # automatic claim of semantic Rule/Decision applicability.
        # Ambiguous/unmapped and high-risk/history requests retain baseline
        # Context and expose a review-needed marker, preventing silent misses.
        can_restrict = (
            scope_route["status"] == "unique"
            and args.risk != "high"
            and args.intent not in {"decision", "history"}
            and scope_route["truncated_candidates"] == 0
        )
        scope_route["restricted_selection"] = can_restrict
        if can_restrict:
            home = scope_route["domains"][0]
            known_paths = all_candidate_paths
            # A source-scored exact Decision explicitly named in the task
            # must survive even if it belongs to ANOTHER Domain. Preserve it
            # as a review candidate, never as asserted applicable authority.
            cross_domain_exact = [
                item for item in candidate_results
                if item.get("artifact_type") == "decision"
                and item.get("path") not in known_paths
                and exact_match_priority(item.get("reasons", [])) > 0
            ]
            grounded = [
                item for item in candidate_results
                if item.get("path") == home["path"] or (
                    (item.get("path") in known_paths
                     or item.get("id") in required_rules
                     or item in cross_domain_exact)
                    and exact_match_priority(item.get("reasons", [])) > 0
                )
            ]
            if not any(x.get("path") == home["path"] for x in grounded):
                grounded.insert(0, {
                    "path": home["path"], "id": home["id"],
                    "artifact_type": "domain", "title": home["title"],
                    "status": "confirmed", "domains": [],
                    "score": 2000, "reasons": ["explicit Domain routing"],
                    "mixed_authority": False, "verification": [],
                })
            candidate_results = grounded
        elif scope_route["status"] == "unique":
            # High-risk, history and overflow keep EVERY normal lexical
            # candidate, but must still carry the confirmed Domain that made
            # this a unique route. Prefer its existing lexical result if any.
            home = scope_route["domains"][0]
            existing = next(
                (item for item in candidate_results
                 if item.get("path") == home["path"]), None,
            )
            domain = existing or {
                "path": home["path"], "id": home["id"],
                "artifact_type": "domain", "title": home["title"],
                "status": "confirmed", "domains": [],
                "score": 2000, "reasons": ["explicit Domain routing"],
                "mixed_authority": False, "verification": [],
            }
            candidate_results = [domain] + [
                item for item in candidate_results
                if item.get("path") != home["path"]
            ]

    results, code_results, budget = select_context_candidates(
        candidate_results,
        candidate_code_results,
        token_budget=token_budget,
        knowledge_limit=knowledge_limit,
        code_limit=code_limit,
    )
    if scope_route is not None and scope_route["status"] == "unique":
        domain_path = scope_route["domains"][0]["path"]
        if not any(item.get("path") == domain_path for item in results):
            print(
                "PACT context: scoped Domain landing page was not materialized "
                "under the knowledge count/token budget; increase --limit or "
                "--token-budget, or rerun without --scope-first",
                file=sys.stderr,
            )
            return 2
    code_candidate_hints = (
        build_code_candidate_hints(candidate_code_results, code_results)
        if preserve_primary
        else []
    )

    domains = sorted({
        domain
        for result in results
        for domain in result.get("domains", [])
    })

    rules = applicable_rule_ids(results)
    exact_required: dict[str, dict | None] = {}
    for rule_id in required_rules:
        if rule_id in rules or any(
            item.get("id") == rule_id for item in candidate_results
        ):
            continue
        try:
            exact_discovery = run_discovery(
                [rule_id], knowledge_pool_limit, code=False,
                code_limit=code_limit,
            )
        except Exception as exc:
            print(f"PACT context: cannot verify required Rule {rule_id}: {exc}",
                  file=sys.stderr)
            return 2
        exact_required[rule_id] = next(
            (item for item in exact_discovery.get("results", [])
             if item.get("id") == rule_id),
            None,
        )
    gaps = required_rule_gaps(
        required_rules, results, candidate_results, exact_required
    )
    if gaps:
        for gap in gaps:
            print(f"PACT context: {gap}", file=sys.stderr)
        return 2

    decisions = sorted({
        result["id"] or result["path"]
        for result in results
        if result.get("artifact_type") == "decision"
        and result.get("status") == "implemented"
    })
    verification = sorted({
        target
        for result in results
        if not result.get("mixed_authority")
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

    unknowns: list[str] = governance_path_hints()
    unknowns.extend(nearby_readme_hints(code_results))
    if scope_route is not None:
        if scope_route.get("restricted_selection") and cross_domain_exact:
            unknowns.append(
                "An explicitly identified cross-Domain Decision was retained as "
                "a candidate, NOT automatically applicable authority: "
                + ", ".join(sorted(str(item["path"]) for item in cross_domain_exact))
                + ". Verify its premises and Owner scope before changing behavior."
            )
        if scope_route["status"] != "unique":
            unknowns.append(
                "Domain routing was not unique; baseline lexical Context was retained. "
                "Do not assume candidate Decisions are applicable without verifying "
                "the business behavior and explicit authority."
            )
        elif scope_route["restricted_selection"]:
            unknowns.append(
                "Domain-first Context holds only explicitly scoped/ID-title-alias "
                "knowledge. Linked Rules and Decisions are candidate hints, NOT "
                "confirmed applicable authority; inspect them before changing "
                "related behavior. For cross-domain or uncertain work, rerun "
                "without --scope-first or with --risk high."
            )
        else:
            unknowns.append(
                "Domain metadata was found but high-risk/history Context remains "
                "unrestricted: verify cross-domain current rules and decisions."
            )
        if scope_route["truncated_candidates"]:
            unknowns.append(
                f"{scope_route['truncated_candidates']} Domain-associated authority "
                "candidates exceeded the metadata cap; selection was NOT narrowed. "
                "Review the complete Domain source and cross-domain references "
                "before claiming context sufficiency."
            )
    mixed_candidates = sorted({
        str(result.get("path"))
        for result in candidate_results
        if result.get("mixed_authority") and result.get("path")
    })
    if mixed_candidates:
        unknowns.append(
            "Confirmed Rule artifact(s) contain explicitly unconfirmed sections: "
            + ", ".join(mixed_candidates)
            + ". Their file-level status is ambiguous; split confirmed and "
            "candidate rules before treating them as applicable normative truth."
        )
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
    if code_candidate_hints:
        unknowns.append(
            f"{len(code_candidate_hints)} non-materialized fallback code candidate "
            "hint(s) are available; inspect them selectively when they could "
            "materially change the task before expanding Context budgets."
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
                "mixed_authority": bool(item.get("mixed_authority", False)),
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

    if code_candidate_hints:
        envelope["code_candidate_hints"] = code_candidate_hints
    if scope_route is not None:
        envelope["scope_route"] = scope_route
        # Final post-materialization check: do not publish a packet combining
        # old Domain routing metadata with a newer Domain artifact digest.
        # This also catches edits after the earlier source verification.
        try:
            final_route = route_only(args.task, ROOT)
            final_metadata = {
                key: value for key, value in final_route.items()
                if key != "candidates"
            }
            if (final_metadata != original_metadata
                    or final_route["candidates"] != recorded):
                raise ValueError("Domain routing changed before Context publication")
            if any(
                artifact_sha256(relative) != digest
                for relative, digest in scope_source_hashes.items()
            ):
                raise ValueError("Domain/authority sources changed before Context publication")
            if any(
                item["sha256"] != scope_source_hashes[item["path"]]
                for item in envelope["artifacts"]
                if item["path"] in scope_source_hashes
            ):
                raise ValueError("Context mixes Domain/authority source generations")
        except (ValueError, OSError, RuntimeError) as exc:
            print(f"PACT context: inconsistent Domain source snapshot: {exc}",
                  file=sys.stderr)
            return 2

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
