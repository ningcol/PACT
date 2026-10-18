#!/usr/bin/env python3
"""Public source, author-labelled lexical noise diagnostic; never a real Agent A/B.

The 12 task strings and their developer oracle are precommitted Git blobs.
This runner NEVER changes frozen tasks, oracle, PACT defaults or upstream Git.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys

import brownfield_adr_viewer as pilot
import decision_memory_m0 as m0


ROOT = pathlib.Path(__file__).resolve().parents[2]
CASES = ROOT / "benchmarks" / "decision-memory" / "noise-cases-v1.json"
ORACLE = ROOT / "benchmarks" / "decision-memory" / "noise-developer-oracle-v1.json"
CASES_BLOB = "9d30fd10a7f2befca9b111542115a3d506bf82e5"
ORACLE_BLOB = "fb8fc5960b98e3e68195b78f14cbd45431fae367"
FROZEN_PACT_BASELINE = "8d10a7bfde791a84da12742e2302704f706fd796"


def load_frozen_cases() -> dict:
    if pilot.git_blob_sha(CASES) != CASES_BLOB:
        raise ValueError("noise case task text or frozen settings changed")
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    if (cases.get("version") != 1
            or cases.get("pact_source_baseline") != FROZEN_PACT_BASELINE
            or cases.get("external_source") != pilot.EXPECTED_UPSTREAM
            or cases.get("external_sha") != pilot.EXPECTED_UPSTREAM_SHA):
        raise ValueError("noise source baseline does not match precommitted test")
    canonical = json.loads(pilot.CARDS.read_text(encoding="utf-8"))
    if cases.get("settings") != canonical["settings"]:
        raise ValueError("noise task budget and runtime intent were changed")
    tasks = cases.get("cases")
    if not isinstance(tasks, list) or len(tasks) != 12:
        raise ValueError("noise probe must have exactly 12 preregistered tasks")
    if len({c["id"] for c in tasks}) != 12:
        raise ValueError("duplicate frozen noise case ID")
    negatives = sum(c["type"] == "routine-negative" for c in tasks)
    positives = sum(c["type"] == "decision-conflict" for c in tasks)
    if (negatives, positives) != (8, 4):
        raise ValueError("frozen negative and positive denominators changed")
    if any(
        "DEC-ADR-" in c["task"] or not c["task"].strip()
        for c in tasks
    ):
        raise ValueError("test task leaked target Decision ID")
    return cases


def load_frozen_oracle(cases: dict) -> dict:
    if pilot.git_blob_sha(ORACLE) != ORACLE_BLOB:
        raise ValueError("noise developer oracle modified")
    oracle = json.loads(ORACLE.read_text(encoding="utf-8"))
    task_ids = {c["id"] for c in cases["cases"]}
    expected = oracle.get("expected_current")
    if (not isinstance(expected, dict) or set(expected) != task_ids
            or len([key for key, value in expected.items() if value]) != 4
            or not all(isinstance(v, list) for v in expected.values())):
        raise ValueError("noise oracle changed case count/denominator")
    return oracle


def extract_scored_discover(target: pathlib.Path, cases: dict) -> list[dict]:
    """Record the *installed PACT CLI* numeric scores and reasons before oracle."""
    records = []
    setup = cases["settings"]
    for card in cases["cases"]:
        args = [
            "discover", card["task"], "--intent", setup["intent"],
            "--json", "--limit", str(setup["knowledge_limit"]),
        ]
        response = m0.run_json(target, args)
        if response["returncode"] != 0:
            raise RuntimeError("diagnostic discover returned nonzero; " +
                               str(response.get("stdout_excerpt", ""))[:500])
        body = response.get("data")
        if not isinstance(body, dict) or not isinstance(body.get("results"), list):
            raise ValueError("successful diagnostic discover had malformed JSON schema")
        hits = body["results"]
        if any(not pilot.valid_discovery_result(x) for x in hits):
            raise ValueError("diagnostic discover returned malformed nested hits")
        records.append({
            "id": card["id"],
            "command": response["command"],
            "elapsed_ms": response["elapsed_ms"],
            "hits": [
                {
                    "id": x.get("id"), "path": x.get("path"),
                    "status": x.get("status"), "type": x.get("artifact_type"),
                    "score": x.get("score"), "reasons": x.get("reasons"),
                }
                for x in hits
            ],
        })
    return records


def evaluate(target: pathlib.Path, progress: dict) -> dict:
    cases = load_frozen_cases()
    source = json.loads(pilot.CARDS.read_text(encoding="utf-8"))
    progress["stage"] = "verify-original-repository"
    pilot.validate_frozen(source, target)
    original_blobs = {
        entry["source"]: pilot.git_blob_sha(target / entry["source"])
        for entry in source["upstream_docs"]
    }
    cards = {**source, "tasks": [
        {"id": x["id"], "task": x["task"], "kind": x["type"]}
        for x in cases["cases"]
    ]}
    progress["stage"] = "install-source-identical-pact"
    progress["install"] = pilot.install_pact(target)
    progress["initial_knowledge"] = pilot.source_snapshot(target)
    if progress["initial_knowledge"]:
        raise ValueError("original upstream had unexpected pre-existing PACT notes")
    progress["stage"] = "A-legacy-no-PACT-decisions"
    progress["A"] = []
    pilot.probe(target, cards, progress["A"])
    progress["A_scored"] = extract_scored_discover(target, cases)

    progress["stage"] = "B-project-original-source-ADRs"
    progress["projected_paths"] = pilot.project_adrs(target, source)
    progress["knowledge_expected"] = pilot.source_snapshot(target)
    progress["stage"] = "B-installed-Pact-check"
    checked = subprocess.run(
        [sys.executable, str(target / "pact.py"), "check"],
        cwd=target, text=True, capture_output=True, timeout=90, check=False,
    )
    progress["pact_check"] = {
        "returncode": checked.returncode, "stdout": checked.stdout[:1000],
        "stderr": checked.stderr[:1000],
    }
    if checked.returncode:
        raise ValueError("PACT check failed after projection")
    progress["stage"] = "B-projected-ADRs"
    progress["B"] = []
    pilot.probe(target, cards, progress["B"])
    progress["B_scored"] = extract_scored_discover(target, cases)
    progress["stage"] = "verify-no-unintended-knowledge-changes"
    progress["knowledge_after"] = pilot.source_snapshot(target)
    progress["original_adr_blobs_after"] = {
        entry["source"]: pilot.git_blob_sha(target / entry["source"])
        for entry in source["upstream_docs"]
    }
    progress["original_adrs_unmodified"] = (
        original_blobs == progress["original_adr_blobs_after"]
        and not pilot.git_output(target, "status", "--porcelain", "--untracked-files=no")
    )
    return progress


def score(progress: dict, cases: dict, oracle: dict) -> dict:
    original = json.loads(pilot.CARDS.read_text(encoding="utf-8"))
    if len(progress["A"]) != 12 or len(progress["B"]) != 12:
        raise ValueError("missing paired noise predictions")
    if len(progress["A_scored"]) != 12 or len(progress["B_scored"]) != 12:
        raise ValueError("missing scored Discover receipts")
    expected_ids = [x["id"] for x in cases["cases"]]
    if ([r["id"] for r in progress["A"]] != expected_ids
            or [r["id"] for r in progress["B"]] != expected_ids):
        raise ValueError("case IDs reordered or missing")
    known = {x["id"]: x["status"] for x in original["upstream_docs"]}
    failure = []
    if not progress["original_adrs_unmodified"]:
        failure.append("original public GitHub source changed during diagnostic")
    if progress["knowledge_expected"] != progress["knowledge_after"]:
        failure.append("long-term PACT memory changed during diagnostic")
    if len(progress["knowledge_after"]) != 6:
        failure.append("wrong number of projected source-authored Decisions")
    if progress["pact_check"]["returncode"] != 0:
        failure.append("installed PACT check failed")
    if not progress["install"].get("installed_source_match"):
        failure.append("installed runtime/source digest mismatch")
    no_target_count = 0
    no_target_with_noise = 0
    positive_targets = matched_targets = 0
    all_extra = 0
    all_current = 0
    total_est_a = total_est_b = 0
    output = []
    for i, card in enumerate(cases["cases"]):
        aid = card["id"]
        a = progress["A"][i]
        b = progress["B"][i]
        b_scored = progress["B_scored"][i]
        expected = set(oracle["expected_current"][aid])
        current = set(b["context"]["current_decision_ids"])
        hit = expected & current
        extra = sorted(current - expected)
        all_extra += len(extra)
        all_current += len(current)
        positive_targets += len(expected)
        matched_targets += len(hit)
        if not expected:
            no_target_count += 1
            no_target_with_noise += bool(extra)
        for phase, v in (("A", a), ("B", b)):
            d, c = v["discovery"], v["context"]
            if d["returncode"] or c["returncode"] or d["schema_errors"] or c["schema_errors"]:
                failure.append(f"{aid}/{phase}: invalid CLI result")
            if c["status"] != "candidate" or c["code_context_selected"]:
                failure.append(f"{aid}/{phase}: incorrect Context/no-code state")
            if c["selected_knowledge_files"] > cases["settings"]["knowledge_limit"]:
                failure.append(f"{aid}/{phase}: knowledge count exceeded")
            tokens = c["estimated_selected_tokens"]
            if not isinstance(tokens, int) or tokens > cases["settings"]["estimated_token_budget"]:
                failure.append(f"{aid}/{phase}: invalid token estimate or over-budget")
            if any(known.get(v) != "implemented" for v in c["current_decision_ids"]):
                failure.append(f"{aid}/{phase}: historical/unknown Decision became current")
        total_est_a += a["context"]["estimated_selected_tokens"]
        total_est_b += b["context"]["estimated_selected_tokens"]
        output.append({
            "id": aid, "classification": card["type"],
            "expected_current": sorted(expected),
            "A_current": a["context"]["current_decision_ids"],
            "B_current": sorted(current),
            "B_target_hits": sorted(hit),
            "B_target_misses": sorted(expected-current),
            "B_extraneous_current": extra,
            "B_estimated_selected_tokens": b["context"]["estimated_selected_tokens"],
            "B_scored_hits": b_scored["hits"],
            "agent_behavior_observed": False,
        })
    return {
        "kind": "real pinned public source; developer-authored synthetic lexical-noise diagnostic",
        "baseline_source_sha": FROZEN_PACT_BASELINE,
        "evaluated_runtime_sha": progress["install"]["source_checkout_git_sha"],
        "installed_runtime_sha256": progress["install"]["installed_archive_sha256"],
        "source_repository": cases["external_source"],
        "source_sha": cases["external_sha"],
        "precommitted_cases_git_blob": CASES_BLOB,
        "precommitted_oracle_git_blob": ORACLE_BLOB,
        "case_count": len(expected_ids),
        "routine_cases": no_target_count,
        "routine_cases_with_extra_current_decisions": no_target_with_noise,
        "positive_target_decisions": positive_targets,
        "positive_target_hits": matched_targets,
        "oracle_extraneous_current_candidates": all_extra,
        "total_current_decision_candidates": all_current,
        "context_estimated_tokens_A_total": total_est_a,
        "context_estimated_tokens_B_total": total_est_b,
        "raw_knowledge_source_mutation": progress["knowledge_expected"] != progress["knowledge_after"],
        "upstream_source_unmodified": progress["original_adrs_unmodified"],
        "engineering_gate": "PASS" if not failure else "FAIL",
        "gate_failures": failure,
        "retrieval_quality": "HOLD" if (
            no_target_with_noise > 0 or matched_targets != positive_targets
        ) else "DEVELOPER_DIAGNOSTIC_ONLY",
        "independent_holdout": False,
        "real_agent_executed": False,
        "real_owner_observed": False,
        "real_model_tokens": None,
        "release_gate": "HOLD",
        "cases": output,
        "raw_receipts": progress,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    args = parser.parse_args()
    progress: dict = {}
    try:
        if os.environ.get("GITHUB_ACTIONS") != "true":
            raise ValueError("requires isolated PACT-owned CI runner")
        target = pathlib.Path(args.target).resolve(strict=True)
        temp = pathlib.Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
        if not target.is_relative_to(temp) or target == temp:
            raise ValueError("target is not a disposable clone under RUNNER_TEMP")
        evaluate(target, progress)
        # Read authored oracle ONLY AFTER predictions are collected.
        cases = load_frozen_cases()
        oracle = load_frozen_oracle(cases)
        result = score(progress, cases, oracle)
    except Exception as error:
        result = {
            "kind": "real public source developer-noise diagnostic",
            "engineering_gate": "FAIL",
            "gate_failures": [f"{type(error).__name__}: {error}"],
            "partial_receipts": progress,
            "independent_holdout": False, "real_agent_executed": False,
            "real_owner_observed": False, "release_gate": "HOLD",
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["engineering_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
