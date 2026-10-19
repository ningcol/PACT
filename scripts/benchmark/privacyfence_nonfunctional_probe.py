#!/usr/bin/env python3
"""Supplemental *nonblind*, *no-model* public PrivacyFence routine-task probe.

Never changes prior 12-case A/B scoring, frozen cases, developer oracle, source
ADRs, or the original repository. Results cannot establish Agent obedience.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import traceback

import privacyfence_pilot as pilot

EXPECTED_NEGATIVES = 2


def paired_metrics(baseline: list[dict], opt_in: list[dict]) -> dict:
    base = {x["id"]: x for x in baseline if x.get("kind") == "routine-negative"}
    got = {x["id"]: x for x in opt_in}
    source_negatives = [x for x in baseline if x.get("kind") == "routine-negative"]
    if (len(source_negatives) != EXPECTED_NEGATIVES
            or len(opt_in) != EXPECTED_NEGATIVES
            or len(base) != EXPECTED_NEGATIVES
            or len(got) != EXPECTED_NEGATIVES
            or set(base) != set(got)):
        raise ValueError("mismatched frozen routine-task pair count/IDs")

    return {
        "baseline_routine_cases_with_current_decisions": sum(
            bool(x["source_verified_decisions"]) for x in base.values()
        ),
        "opt_in_routine_cases_with_current_decisions": sum(
            bool(x["source_verified_decisions"]) for x in got.values()
        ),
        "baseline_routine_selected_estimated_tokens": sum(
            x["budget"]["selected_estimated_tokens"] for x in base.values()
        ),
        "opt_in_routine_selected_estimated_tokens": sum(
            x["budget"]["selected_estimated_tokens"] for x in got.values()
        ),
        "per_case": [
            {
                "id": ident,
                "baseline_current_decision_ids": base[ident]["source_verified_decisions"],
                "opt_in_current_decision_ids": got[ident]["source_verified_decisions"],
                "baseline_estimated_tokens": base[ident]["budget"]["selected_estimated_tokens"],
                "opt_in_estimated_tokens": got[ident]["budget"]["selected_estimated_tokens"],
                "nonfunctional_hints": got[ident].get("nonfunctional_decision_hints"),
            }
            for ident in sorted(base)
        ],
    }


def trial(target: pathlib.Path, baseline_receipt: dict) -> dict:
    report = {
        "kind": "nonblind-opt-in-nonfunctional-routine-source-probe",
        "pact_source_commit": pilot.pilot.git_output(pilot.ROOT, "rev-parse", "HEAD"),
        "source_repo": pilot.UPSTREAM,
        "source_sha": pilot.UPSTREAM_SHA,
        "real_agent_executed": False,
        "independent_holdout": False,
        "authenticated_owner_observation": False,
        "provider_billed_tokens": None,
        "release_gate": "HOLD",
        "stage": "preflight",
        "failures": [],
    }
    try:
        cards = pilot.verify_freeze(target)
        if (baseline_receipt.get("engineering_gate") != "PASS"
                or baseline_receipt.get("source_sha") != pilot.UPSTREAM_SHA
                or baseline_receipt.get("case_manifest_blob") != pilot.CASES_BLOB
                or baseline_receipt.get("developer_oracle_blob") != pilot.ORACLE_BLOB
                or baseline_receipt.get("real_agent_executed") is not False
                or baseline_receipt.get("tracked_upstream_clean") is not True
                or baseline_receipt.get("source_blobs_unchanged") is not True
                or baseline_receipt.get("projection_digests_unchanged") is not True):
            raise ValueError("baseline A/B receipt is not source-verified PASS")
        expected = {pilot.target_path(doc) for doc in cards["source_docs"]}
        digests = baseline_receipt.get("projected_source_sha256")
        if not isinstance(digests, dict) or set(digests) != expected:
            raise ValueError("baseline does not bind all frozen Decision projections")
        for rel, digest in digests.items():
            if pilot.m0.digest_file(pilot.safe_source(target, rel)) != digest:
                raise ValueError(f"source projection changed: {rel}")
        original = baseline_receipt["arms"]["B_source_projection"]
        if len(original) != pilot.EXPECTED_COUNT:
            raise ValueError("missing source-verified baseline cases")
        routine = [c for c in cards["tasks"] if c["kind"] == "routine-negative"]
        if len(routine) != EXPECTED_NEGATIVES:
            raise ValueError("wrong frozen routine denominator")
        report["stage"] = "installed-source-equivalent-nonfunctional"
        report["routines"] = []
        pilot.run_arm(
            target, {**cards, "tasks": routine},
            "B_nonfunctional_routines", result=report["routines"],
            context_options=["--nonfunctional"],
        )
        report["stage"] = "source-integrity-and-scoring"
        for item in report["routines"]:
            report["failures"].extend(
                f"{item['id']}: {err}" for err in item["schema_and_source_errors"]
            )
            if item["context_returncode"] != 0 or item["discover_returncode"] != 0:
                report["failures"].append(f"{item['id']}: installed PACT failed")
            if item["source_verified_decisions"]:
                report["failures"].append(
                    f"{item['id']}: implicit Decision still auto-materialized "
                    "despite explicit nonfunctional task mode"
                )
            hints = item.get("nonfunctional_decision_hints")
            if not isinstance(hints, dict):
                report["failures"].append(f"{item['id']}: missing bounded source hints")
        report["paired_developer_observation"] = paired_metrics(original, report["routines"])
        report["tracked_upstream_clean"] = not pilot.pilot.git_output(
            target, "status", "--porcelain", "--untracked-files=no"
        )
        report["frozen_projected_sources_unchanged"] = all(
            pilot.m0.digest_file(pilot.safe_source(target, rel)) == digest
            for rel, digest in digests.items()
        )
        if not report["tracked_upstream_clean"]:
            report["failures"].append("original upstream tracked source was modified")
        if not report["frozen_projected_sources_unchanged"]:
            report["failures"].append("pre-frozen source projections changed")
        report["stage"] = "done"
    except Exception as exc:
        report["failures"].append(f"{type(exc).__name__}: {exc}")
        report["exception_traceback"] = traceback.format_exc(limit=8)
    report["engineering_gate"] = "PASS" if not report["failures"] else "FAIL"
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--baseline", required=True)
    args = parser.parse_args()
    path = pathlib.Path(args.baseline).resolve()
    baseline = json.loads(path.read_text(encoding="utf-8"))
    receipt = trial(pathlib.Path(args.target).resolve(), baseline)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["engineering_gate"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
