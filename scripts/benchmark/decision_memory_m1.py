#!/usr/bin/env python3
"""M1: no-ID cold-start retrieval plus bounded path navigation, synthetic only.

M1 does NOT run an LLM Agent, observe Owner permission, or certify adherence.
The developer-authored oracle is read only after all installed-CLI predictions.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys
import tempfile

import decision_memory_m0 as m0


ROOT = pathlib.Path(__file__).resolve().parents[2]
CARDS = ROOT / "benchmarks" / "decision-memory" / "m1-task-cards.json"
ORACLE = ROOT / "benchmarks" / "decision-memory" / "m1-oracle.json"
CARDS_BLOB = "5b5c80d2f772c75d3c7984c0ffbc2d380870a6fa"
ORACLE_BLOB = "bba20149d96b624bc6d9cae09008b91a1c9bfe44"
M0_CORPUS_BLOB = "14693c6b209b8ef734edbd9e3e9842efd5bca3cd"
CASE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
MAX_CASES = 8
ALLOWED_STATUS = {"implemented", "superseded", "rejected", "archived"}


def blob_sha(path: pathlib.Path) -> str:
    payload = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(payload)).encode("ascii")
                        + b"\0" + payload).hexdigest()


def validate_cards(cards: dict, corpus: dict) -> None:
    if blob_sha(CARDS) != CARDS_BLOB or blob_sha(m0.INPUTS) != M0_CORPUS_BLOB:
        raise ValueError("M1 frozen task cards or M0 source corpus were changed")
    m0.validate_inputs(corpus)
    settings = cards.get("settings")
    if not isinstance(settings, dict) or settings != {
        "intent": "work", "knowledge_limit": 4, "token_budget": 2048,
        "code_context": False, "risk": "low",
        "success": "Preserve applicable existing decisions before modifying the named behavior",
        "max_path_hints": 4,
    }:
        raise ValueError("M1 frozen Context settings were changed")
    cases = cards.get("cases")
    if not isinstance(cases, list) or len(cases) != MAX_CASES:
        raise ValueError("M1 requires all eight preregistered cases")
    ids = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(ids) != MAX_CASES or len(set(ids)) != MAX_CASES or not all(
        isinstance(value, str) and CASE_ID.fullmatch(value) for value in ids
    ):
        raise ValueError("M1 cases must have unique safe IDs")
    allowed_paths = {entry["path"] for entry in corpus["code_files"]}
    for case in cases:
        task = case.get("task")
        paths = case.get("changed_paths")
        if (
            not isinstance(task, str) or not task.strip() or "DEC-" in task.upper()
            or case.get("explicit_decision_hint") is not None
            or not isinstance(paths, list) or len(paths) > 4
            or len(paths) != len(set(paths)) or
            any(not isinstance(path, str) or path not in allowed_paths
                for path in paths)
        ):
            raise ValueError(f"M1 case leaks hints or invalid code paths: {case.get('id')}")
    if cards.get("m0_corpus_blob_sha") != M0_CORPUS_BLOB:
        raise ValueError("M1 corpus provenance mismatch")


def validate_oracle(oracle: dict, cards: dict, corpus: dict) -> None:
    if blob_sha(ORACLE) != ORACLE_BLOB:
        raise ValueError("M1 frozen scoring oracle was changed")
    ids = {case["id"] for case in cards["cases"]}
    if (oracle.get("version") != 1
            or set(oracle.get("expected_current", {})) != ids
            or set(oracle.get("relevant_history", {})) != ids):
        raise ValueError("M1 frozen oracle case set mismatch")
    docs = {doc["id"]: doc for doc in corpus["documents"]}
    for case in cards["cases"]:
        cid = case["id"]
        current = oracle["expected_current"][cid]
        history = oracle["relevant_history"][cid]
        if (not isinstance(current, list) or not isinstance(history, list)
                or len(set(current)) != len(current)
                or len(set(history)) != len(history)
                or any(doc_id not in docs or docs[doc_id]["type"] != "decision"
                       or docs[doc_id]["status"] != "implemented" for doc_id in current)
                or any(doc_id not in docs or docs[doc_id]["type"] != "decision"
                       or docs[doc_id]["status"] == "implemented" for doc_id in history)):
            raise ValueError(f"M1 oracle status mismatch in {cid}")


def source_snapshot(target: pathlib.Path) -> dict[str, str]:
    """Include filenames as well as hashes, so additions/deletions are visible."""
    sources = []
    for relative in (".agents/decisions", "docs/product/rules"):
        folder = target / relative
        if folder.exists():
            sources.extend(folder.rglob("*.md"))
    data = {}
    for path in sources:
        if path.is_symlink() or not path.resolve().is_relative_to(target.resolve()):
            raise ValueError("fixture knowledge symlink escape")
        data[path.relative_to(target).as_posix()] = m0.digest_file(path)
    return dict(sorted(data.items()))


def context_probe(target: pathlib.Path, case: dict, settings: dict) -> dict:
    """Run the actual installed pact.py; no external ID or query expansion."""
    task = case["task"]
    discovery = m0.run_json(target, [
        "discover", task, "--limit", str(settings["knowledge_limit"]),
        "--intent", settings["intent"], "--json",
    ])
    envelope = m0.run_json(target, [
        "context", task, "--success", settings["success"],
        "--risk", settings["risk"], "--intent", settings["intent"],
        "--no-code", "--limit", str(settings["knowledge_limit"]),
        "--token-budget", str(settings["token_budget"]),
    ])
    disc = discovery["data"] if isinstance(discovery["data"], dict) else {}
    packet = envelope["data"] if isinstance(envelope["data"], dict) else {}
    artifacts = packet.get("artifacts")
    if not isinstance(artifacts, list):
        artifacts = []
    budget = packet.get("context_budget")
    if not isinstance(budget, dict):
        budget = {}
    return {
        "discovery": {
            "command": discovery["command"],
            "returncode": discovery["returncode"],
            "elapsed_ms": discovery["elapsed_ms"],
            "stderr": discovery["stderr"],
            "hits": [
                {"id": hit.get("id"), "status": hit.get("status"),
                 "type": hit.get("artifact_type"), "path": hit.get("path")}
                for hit in disc.get("results", [])
                if isinstance(hit, dict)
            ] if isinstance(disc.get("results", []), list) else [],
        },
        "context": {
            "command": envelope["command"],
            "returncode": envelope["returncode"],
            "elapsed_ms": envelope["elapsed_ms"],
            "stderr": envelope["stderr"],
            "status": packet.get("status"),
            "selected_ids": [x.get("id") for x in artifacts if isinstance(x, dict)],
            "current_decision_ids": packet.get("decisions"),
            "applicable_rule_ids": packet.get("applicable_rules"),
            "selected_knowledge_files": len(artifacts),
            "estimated_selected_tokens": budget.get("selected_estimated_tokens"),
            "code_files": len(packet.get("code_artifacts") or []),
            "known_unknown_count": len(packet.get("known_unknowns") or []),
        },
    }


def path_diagnostic(index: dict, changed_paths: list[str], limit: int) -> dict:
    """Candidate lookup only, *not* another Context arm or authority claim."""
    current, historical = [], []
    matches = 0
    for doc in index.get("documents", []):
        if not isinstance(doc, dict) or doc.get("artifact_type") != "decision":
            continue
        anchors = doc.get("paths", [])
        if not isinstance(anchors, list):
            continue
        if not any(path in anchors for path in changed_paths):
            continue
        matches += 1
        status = doc.get("status")
        entry = {"id": doc.get("id"), "status": status, "source": doc.get("path"),
                 "matched_paths": [path for path in changed_paths if path in anchors]}
        if status == "implemented":
            current.append(entry)
        elif status in ALLOWED_STATUS:
            historical.append(entry)
    current.sort(key=lambda x: (str(x["id"]), str(x["source"])))
    historical.sort(key=lambda x: (str(x["id"]), str(x["source"])))
    # Bound the entire navigation payload, including historical candidates.
    candidates = (current + historical)[:limit]
    return {
        "method": "exact-public-changed-path-to-index-metadata-only",
        "current_candidates": [x for x in candidates if x["status"] == "implemented"],
        "historical_candidates": [x for x in candidates if x["status"] != "implemented"],
        "total_raw_matches": matches,
        "omitted_candidates": max(0, matches - len(candidates)),
        "injected_into_context": False,
        "retrieval_treatment": False,
    }


def collect(cards: dict, corpus: dict) -> dict:
    with tempfile.TemporaryDirectory(prefix="pact-m1-cold-start-") as tmp:
        target = pathlib.Path(tmp) / "project"
        installed = m0.install_fixture(target, corpus)
        baseline = source_snapshot(target)
        if len(baseline) != len(corpus["documents"]):
            raise ValueError("unexpected pre-existing durable knowledge in fixture")
        predictions = []
        for case in cards["cases"]:
            # Collect A BEFORE looking up public path metadata or consulting oracle.
            a = context_probe(target, case, cards["settings"])
            index_path = target / ".pact" / "cache" / "project-map.json"
            if not index_path.is_file() or index_path.is_symlink():
                raise ValueError("installed Project Map not generated safely")
            index = json.loads(index_path.read_text(encoding="utf-8"))
            b = path_diagnostic(
                index, case["changed_paths"],
                cards["settings"]["max_path_hints"],
            )
            predictions.append({
                "id": case["id"], "task": case["task"],
                "type": case["type"], "changed_paths": case["changed_paths"],
                "A": a, "B_path_navigation_only": b,
            })
        end = source_snapshot(target)
        mutations = sorted(
            name for name in baseline.keys() | end.keys()
            if baseline.get(name) != end.get(name)
        )
        existing = {entry["path"] for entry in corpus["code_files"]}
        stale = sorted({
            (doc["id"], path)
            for doc in corpus["documents"] if doc["type"] == "decision"
            for path in doc.get("paths", [])
            if path not in existing
        })
    return {
        "predictions": predictions, "installation": installed,
        "knowledge_files_before": len(baseline),
        "knowledge_files_after": len(end),
        "knowledge_source_mutations": mutations,
        "stale_declared_code_anchors": [
            {"decision_id": ident, "path": path} for ident, path in stale
        ],
    }


def score(evidence: dict, oracle: dict, cards: dict, corpus: dict) -> dict:
    validate_oracle(oracle, cards, corpus)
    docs = {doc["id"]: doc for doc in corpus["documents"]}
    predictions = evidence["predictions"]
    if [x["id"] for x in predictions] != [x["id"] for x in cards["cases"]]:
        raise ValueError("M1 prediction set missing/reordered; invalid denominator")
    failures = []
    if evidence["knowledge_source_mutations"]:
        failures.append("durable Decision/Rule source files changed or appeared")
    if evidence["knowledge_files_before"] != evidence["knowledge_files_after"]:
        failures.append("durable knowledge file count changed")
    if not evidence["installation"].get("compact_archive_present"):
        failures.append("installed compact runtime missing")
    target_count = matched = candidate_union_hits = unrelated_selected = 0
    rows = []
    for prediction in predictions:
        cid = prediction["id"]
        a = prediction["A"]
        runtime = a["context"]
        discovery = a["discovery"]
        nav = prediction["B_path_navigation_only"]
        current = runtime.get("current_decision_ids")
        rules = runtime.get("applicable_rule_ids")
        if not isinstance(current, list) or not isinstance(rules, list):
            failures.append(f"{cid}: malformed installed Context authority lists")
            current, rules = [], []
        found = set(current)
        expected = set(oracle["expected_current"][cid])
        history = set(oracle["relevant_history"][cid])
        nav_current = {x["id"] for x in nav["current_candidates"]}
        nav_historical = {x["id"] for x in nav["historical_candidates"]}
        target_count += len(expected)
        matched += len(found & expected)
        candidate_union_hits += len(expected & (found | nav_current))
        unexpected = sorted(found - expected)
        if runtime["returncode"] or discovery["returncode"]:
            failures.append(f"{cid}: installed CLI returned nonzero")
        if runtime["status"] != "candidate":
            failures.append(f"{cid}: unexpected candidate Context status")
        bad = sorted(
            ident for ident in found
            if ident not in docs or docs[ident]["type"] != "decision"
            or docs[ident]["status"] != "implemented"
        )
        bad_rules = sorted(
            ident for ident in rules
            if ident not in docs or docs[ident]["type"] != "rule"
            or docs[ident]["status"] != "confirmed"
        )
        if bad or bad_rules:
            failures.append(f"{cid}: rejected/superseded/nonconfirmed authority promoted")
        if (runtime["selected_knowledge_files"] > cards["settings"]["knowledge_limit"]
                or runtime["code_files"] != 0):
            failures.append(f"{cid}: materialization budget or no-code boundary breached")
        if (not isinstance(runtime["estimated_selected_tokens"], int)
                or runtime["estimated_selected_tokens"] >
                cards["settings"]["token_budget"]):
            failures.append(f"{cid}: selected Context exceeds frozen estimated-token budget")
        if (len(nav["current_candidates"]) + len(nav["historical_candidates"]) >
                cards["settings"]["max_path_hints"]):
            failures.append(f"{cid}: path navigation hint budget exceeded")
        if nav["injected_into_context"] or nav["retrieval_treatment"]:
            failures.append(f"{cid}: path diagnostic mislabeled as runtime retrieval")
        if not expected and found:
            unrelated_selected += len(found)
            failures.append(f"{cid}: unrelated routine task received current Decisions")
        if not expected and nav_current:
            failures.append(f"{cid}: unrelated task received path candidates")
        if any(x not in docs or docs[x]["status"] != "implemented" for x in nav_current):
            failures.append(f"{cid}: wrong current navigation status")
        if any(x not in docs or docs[x]["status"] == "implemented" for x in nav_historical):
            failures.append(f"{cid}: wrong historical navigation status")
        rows.append({
            **prediction,
            "expected_count": len(expected),
            "A_matched": sorted(found & expected),
            "A_missing": sorted(expected - found),
            "A_unexpected_current": unexpected,
            "A_authority_invalid": bad + bad_rules,
            "B_path_current_hit": sorted(expected & nav_current),
            "B_path_historical_for_review": sorted(history & nav_historical),
            "A_or_B_candidate_coverage_not_real_recall":
                sorted(expected & (found | nav_current)),
            "applicability_and_agent_obedience": "unverified",
        })
    return {
        "version": 1,
        "evaluation_kind": "M1 developer-authored synthetic no-ID installed-retrieval and metadata navigation diagnostic",
        "frozen_baseline_main_sha": cards["baseline_main_sha"],
        "frozen_task_cards_git_blob": CARDS_BLOB,
        "frozen_oracle_git_blob": ORACLE_BLOB,
        "frozen_m0_corpus_git_blob": M0_CORPUS_BLOB,
        "case_count": len(rows),
        "target_decision_count": target_count,
        "A_matched_decisions": matched,
        "A_weighted_recall": matched / target_count if target_count else None,
        "B_diagnostic_union_candidate_coverage": candidate_union_hits / target_count if target_count else None,
        "B_is_actual_context_or_agent_recall": False,
        "unexpected_current_decisions_on_routine_task": unrelated_selected,
        "synthetic_safety_gate": "FAIL" if failures else "PASS",
        "gate_failures": failures,
        "cold_start_effectiveness": "HOLD" if matched != target_count else "DIAGNOSTIC_ONLY",
        "independent_real_agent_gate": "BLOCKED_NO_AUTHORIZED_RUNNER",
        "real_agent_executed": False,
        "independent_holdout": False,
        "agent_obedience_verified": False,
        "owner_approval_authenticated": False,
        "owner_clarification_count": None,
        "owner_time_minutes": None,
        "added_model_tokens": None,
        "release_gate": "HOLD",
        "release_attestation": False,
        "installation": evidence["installation"],
        "knowledge_files_before": evidence["knowledge_files_before"],
        "knowledge_files_after": evidence["knowledge_files_after"],
        "knowledge_source_mutations": evidence["knowledge_source_mutations"],
        "stale_declared_code_anchors": evidence["stale_declared_code_anchors"],
        "case_results": rows,
    }


def evaluate() -> dict:
    cards = json.loads(CARDS.read_text(encoding="utf-8"))
    corpus = json.loads(m0.INPUTS.read_text(encoding="utf-8"))
    validate_cards(cards, corpus)
    evidence = collect(cards, corpus)
    # Developer oracle is never read until predictions are complete and the
    # installed disposable project has been destroyed.
    oracle = json.loads(ORACLE.read_text(encoding="utf-8"))
    return score(evidence, oracle, cards, corpus)


def main() -> int:
    if len(sys.argv) != 1:
        raise SystemExit("frozen M1 benchmark accepts no external fixture arguments")
    try:
        result = evaluate()
    except Exception as exc:
        result = {
            "version": 1, "evaluation_kind": "M1 synthetic benchmark failure",
            "synthetic_safety_gate": "FAIL",
            "gate_failures": [f"{type(exc).__name__}: {exc}"],
            "real_agent_executed": False,
            "release_gate": "HOLD",
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["synthetic_safety_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
