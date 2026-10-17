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
import subprocess
import sys
import tempfile

import decision_memory_m0 as m0


ROOT = pathlib.Path(__file__).resolve().parents[2]
CARDS = ROOT / "benchmarks" / "decision-memory" / "m1-task-cards.json"
ORACLE = ROOT / "benchmarks" / "decision-memory" / "m1-oracle.json"
CARDS_BLOB = "5b5c80d2f772c75d3c7984c0ffbc2d380870a6fa"
ORACLE_BLOB = "bba20149d96b624bc6d9cae09008b91a1c9bfe44"
M0_CORPUS_BLOB = "753babf70317c6af1b292b1b031e0afaec503ec3"
# Frozen task-card field mistakenly recorded the M0 *runner* blob instead.
# Keep that frozen field unchanged, and validate its exact recorded mistake.
M0_ORIGINAL_CARD_PROVENANCE_FIELD = "14693c6b209b8ef734edbd9e3e9842efd5bca3cd"
CASE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
MAX_CASES = 8
ALLOWED_STATUS = {"implemented", "superseded", "rejected", "archived"}


def blob_sha(path: pathlib.Path) -> str:
    # Git worktree JSON can have CRLF on Windows while its committed blob is LF.
    # Compare canonical *text bytes*, not checkout-specific line endings.
    payload = path.read_bytes().replace(b"\r\n", b"\n")
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
    if cards.get("m0_corpus_blob_sha") != M0_ORIGINAL_CARD_PROVENANCE_FIELD:
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
            # Detect new/modified notes even if an Agent chose a non-Markdown extension.
            sources.extend(path for path in folder.rglob("*")
                           if path.is_file() or path.is_symlink())
    data = {}
    for path in sources:
        if path.is_symlink() or not path.resolve().is_relative_to(target.resolve()):
            raise ValueError("fixture knowledge symlink escape")
        data[path.relative_to(target).as_posix()] = m0.digest_file(path)
    return dict(sorted(data.items()))


def valid_discovery_hit(hit: object) -> bool:
    if not isinstance(hit, dict):
        return False
    path = hit.get("path")
    if (not isinstance(path, str) or not path or chr(92) in path
            or pathlib.PurePosixPath(path).is_absolute()
            or ".." in pathlib.PurePosixPath(path).parts):
        return False
    kind, ident, status = hit.get("artifact_type"), hit.get("id"), hit.get("status")
    if kind == "document":
        return ident is None and status is None
    if kind in {"decision", "rule"}:
        return (isinstance(ident, str) and
                ident.startswith("DEC-" if kind == "decision" else "RULE-") and
                isinstance(status, str) and bool(status))
    return False


def validate_installed_project_map(index: object, corpus: dict) -> None:
    """Reject malformed/missing frozen IDs; never score a corrupt disposable map."""
    if (not isinstance(index, dict)
            or not isinstance(index.get("documents"), list)
            or not isinstance(index.get("id_to_path"), dict)
            or index.get("repository_root") != "."):
        raise ValueError("installed Project Map has invalid top-level schema")
    expected = {entry["id"]: entry for entry in corpus["documents"]}
    observed = {}
    for entry in index["documents"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ValueError("installed Project Map contains malformed document records")
        if not isinstance(entry.get("artifact_type"), str):
            raise ValueError("installed Project Map has missing artifact type")
        if not isinstance(entry.get("paths"), list) or any(
            not isinstance(p, str) for p in entry.get("paths", [])
        ):
            raise ValueError("installed Project Map has malformed code anchors")
        ident = entry.get("id")
        if ident is None:
            continue
        if (not isinstance(ident, str) or ident in observed
                or ident not in expected):
            raise ValueError("installed Project Map has missing, duplicated or unknown IDs")
        saved = expected[ident]
        if (entry["path"] != saved["path"]
                or entry["artifact_type"] != saved["type"]
                or entry.get("status") != saved["status"]
                or entry["paths"] != saved.get("paths", [])):
            raise ValueError("installed Project Map differs from frozen decision metadata")
        observed[ident] = entry["path"]
    if observed != {ident: entry["path"] for ident, entry in expected.items()}:
        raise ValueError("installed Project Map omits frozen Decision/Rule metadata")
    if index["id_to_path"] != observed:
        raise ValueError("installed Project Map ID lookup disagrees with documents")


def valid_context_artifact(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    path, digest = item.get("path"), item.get("sha256")
    if (not isinstance(path, str) or not path or chr(92) in path
            or pathlib.PurePosixPath(path).is_absolute()
            or ".." in pathlib.PurePosixPath(path).parts
            or not isinstance(digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None):
        return False
    kind, ident = item.get("artifact_type"), item.get("id")
    if kind == "document":
        return ident is None
    if kind in {"decision", "rule"}:
        return isinstance(ident, str) and ident.startswith(
            "DEC-" if kind == "decision" else "RULE-"
        )
    return False


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
    discovery_schema_errors = []
    context_schema_errors = []
    if discovery["returncode"] == 0:
        if not isinstance(discovery["data"], dict):
            discovery_schema_errors.append("successful discover response is not an object")
        if not isinstance(disc.get("results"), list) or any(
            not valid_discovery_hit(hit) for hit in disc.get("results", [])
        ):
            discovery_schema_errors.append("successful discover results have invalid hit/path/type/status records")
    if envelope["returncode"] == 0:
        if not isinstance(envelope["data"], dict):
            context_schema_errors.append("successful context response is not an object")
        for key in ("artifacts", "decisions", "applicable_rules", "code_artifacts", "known_unknowns"):
            if not isinstance(packet.get(key), list):
                context_schema_errors.append(f"context {key} is not a list")
        if not isinstance(packet.get("context_budget"), dict):
            context_schema_errors.append("context budget is not an object")
    artifacts = packet.get("artifacts")
    if not isinstance(artifacts, list):
        artifacts = []
    if any(not valid_context_artifact(item) for item in artifacts):
        context_schema_errors.append("successful Context artifacts have malformed path/type/digest records")
        artifacts = [item for item in artifacts if isinstance(item, dict)]
    budget = packet.get("context_budget")
    if not isinstance(budget, dict):
        budget = {}
    return {
        "discovery": {
            "command": discovery["command"],
            "returncode": discovery["returncode"],
            "elapsed_ms": discovery["elapsed_ms"],
            "stderr": discovery["stderr"],
            "schema_errors": discovery_schema_errors,
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
            "schema_errors": context_schema_errors,
            "status": packet.get("status"),
            "selected_ids": [x.get("id") for x in artifacts if isinstance(x, dict)],
            "selected_artifacts": [
                {"id": x.get("id"), "path": x.get("path"),
                 "artifact_type": x.get("artifact_type"),
                 "sha256": x.get("sha256")}
                for x in artifacts if isinstance(x, dict)
            ],
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


def collect(cards: dict, corpus: dict, progress: dict | None = None) -> dict:
    if progress is None:
        progress = {}
    progress["stage"] = "install"
    with tempfile.TemporaryDirectory(prefix="pact-m1-cold-start-") as tmp:
        target = pathlib.Path(tmp) / "project"
        installed = m0.install_fixture(target, corpus)
        installed_archive = target / installed["compact_runtime_relative"]
        if not installed_archive.is_file() or installed_archive.is_symlink():
            raise ValueError("installed compact runtime artifact not verifiable")
        installed["compact_archive_sha256"] = m0.digest_file(installed_archive)
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
            text=True, timeout=20, check=False,
        )
        installed["source_checkout_git_sha"] = (
            revision.stdout.strip() if revision.returncode == 0 else None
        )
        baseline = source_snapshot(target)
        progress["installation"] = installed
        progress["knowledge_source_sha256"] = baseline
        if len(baseline) != len(corpus["documents"]):
            raise ValueError("unexpected pre-existing durable knowledge in fixture")
        predictions = []
        progress["predictions"] = predictions
        progress["stage"] = "collect-predictions"
        for case in cards["cases"]:
            # Persist this A observation before map validation; preserve it even
            # if Project Map JSON is missing/corrupt or B diagnostics fail.
            a = context_probe(target, case, cards["settings"])
            observation = {
                "id": case["id"], "task": case["task"],
                "type": case["type"], "changed_paths": case["changed_paths"],
                "A": a, "B_path_navigation_only": None,
            }
            predictions.append(observation)
            index_path = target / ".pact" / "cache" / "project-map.json"
            if not index_path.is_file() or index_path.is_symlink():
                raise ValueError("installed Project Map not generated safely")
            index = json.loads(index_path.read_text(encoding="utf-8"))
            validate_installed_project_map(index, corpus)
            b = path_diagnostic(
                index, case["changed_paths"],
                cards["settings"]["max_path_hints"],
            )
            observation["B_path_navigation_only"] = b
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
        "knowledge_source_sha256": baseline,
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
    total_current_candidates = oracle_extraneous = 0
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
        # IDs in the summary are not proof the source document was selected.
        selected_ids = runtime.get("selected_ids")
        if not isinstance(selected_ids, list):
            failures.append(f"{cid}: Context selected artifact IDs are malformed")
            selected_ids = []
        if not found.issubset(set(selected_ids)):
            failures.append(f"{cid}: claimed current Decision not materialized in Context")
        if not set(rules).issubset(set(selected_ids)):
            failures.append(f"{cid}: claimed applicable Rule not materialized in Context")
        # IDs alone are insufficient: require a selected source path, type and
        # content digest matching the frozen installed fixture's actual file.
        selected_records = runtime.get("selected_artifacts")
        if not isinstance(selected_records, list):
            failures.append(f"{cid}: Context selected artifact records are malformed")
            selected_records = []
        for ident in found | set(rules):
            if ident not in docs:
                continue  # Existing authority validation rejects unknown IDs.
            source = docs[ident]
            matching = [
                record for record in selected_records
                if isinstance(record, dict)
                and record.get("id") == ident
                and record.get("path") == source["path"]
                and record.get("artifact_type") == source["type"]
                and isinstance(record.get("sha256"), str)
                and record["sha256"] == evidence.get(
                    "knowledge_source_sha256", {}
                ).get(source["path"])
            ]
            if not matching:
                failures.append(
                    f"{cid}: {ident} missing valid materialized source record"
                )
        expected = set(oracle["expected_current"][cid])
        history = set(oracle["relevant_history"][cid])
        nav_current = {x["id"] for x in nav["current_candidates"]}
        nav_historical = {x["id"] for x in nav["historical_candidates"]}
        target_count += len(expected)
        matched += len(found & expected)
        candidate_union_hits += len(expected & (found | nav_current))
        unexpected = sorted(found - expected)
        total_current_candidates += len(found)
        oracle_extraneous += len(unexpected)
        if runtime["returncode"] or discovery["returncode"]:
            failures.append(f"{cid}: installed CLI returned nonzero")
        if discovery.get("schema_errors") or runtime.get("schema_errors"):
            failures.append(f"{cid}: successful CLI output had malformed discovery/context schema")
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
        "evaluated_source_checkout_git_sha": evidence["installation"].get("source_checkout_git_sha"),
        "evaluated_installed_compact_runtime_sha256": evidence["installation"].get("compact_archive_sha256"),
        "frozen_task_cards_git_blob": CARDS_BLOB,
        "frozen_oracle_git_blob": ORACLE_BLOB,
        "frozen_m0_corpus_git_blob": M0_CORPUS_BLOB,
        "frozen_task_card_corpus_field_mislabeled_m0_runner_blob": M0_ORIGINAL_CARD_PROVENANCE_FIELD,
        "corpus_provenance_correction_documented": True,
        "case_count": len(rows),
        "target_decision_count": target_count,
        "A_matched_decisions": matched,
        "A_total_current_decision_candidates": total_current_candidates,
        "A_oracle_extraneous_current_candidates": oracle_extraneous,
        "A_oracle_candidate_precision_proxy": matched / total_current_candidates if total_current_candidates else None,
        "precision_proxy_is_not_verified_semantic_precision": True,
        "A_weighted_recall": matched / target_count if target_count else None,
        "B_diagnostic_union_candidate_coverage": candidate_union_hits / target_count if target_count else None,
        "B_is_actual_context_or_agent_recall": False,
        "unexpected_current_decisions_on_routine_task": unrelated_selected,
        "synthetic_safety_gate": "FAIL" if failures else "PASS",
        "gate_failures": failures,
        "cold_start_effectiveness": "HOLD" if (matched != target_count or oracle_extraneous) else "DIAGNOSTIC_ONLY",
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
        "knowledge_source_sha256": evidence.get("knowledge_source_sha256", {}),
        "knowledge_source_mutations": evidence["knowledge_source_mutations"],
        "stale_declared_code_anchors": evidence["stale_declared_code_anchors"],
        "case_results": rows,
    }


def evaluate(progress: dict | None = None) -> dict:
    cards = json.loads(CARDS.read_text(encoding="utf-8"))
    corpus = json.loads(m0.INPUTS.read_text(encoding="utf-8"))
    validate_cards(cards, corpus)
    evidence = collect(cards, corpus, progress)
    # Developer oracle is never read until predictions are complete and the
    # installed disposable project has been destroyed.
    oracle = json.loads(ORACLE.read_text(encoding="utf-8"))
    return score(evidence, oracle, cards, corpus)


def main() -> int:
    if len(sys.argv) != 1:
        raise SystemExit("frozen M1 benchmark accepts no external fixture arguments")
    progress: dict = {}
    try:
        result = evaluate(progress)
    except Exception as exc:
        result = {
            "version": 1, "evaluation_kind": "M1 synthetic benchmark failure",
            "synthetic_safety_gate": "FAIL",
            "gate_failures": [f"{type(exc).__name__}: {exc}"],
            "partial_probe_evidence": progress or None,
            "completed_probes_preserved": bool(progress.get("predictions")),
            "real_agent_executed": False,
            "release_gate": "HOLD",
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["synthetic_safety_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
