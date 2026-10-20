#!/usr/bin/env python3
"""Preregistered no-model engineering gates for source-pinned weak Context trials.

Frozen developer-authored public project tasks remain unchanged. These are
materialization/retrieval safety gates, NOT independent real coding-Agent A/B.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

PRIVACYFENCE_SHA = "6a03856a6e1819b2eacd3963154ebc7d02923296"
ADR_VIEWER_SHA = "a25f1c71e031bdaa63fe3175f969f197139f2044"
ORIGINAL_PRIVACYFENCE_POSITIVES = 10
ORIGINAL_PRIVACYFENCE_ROUTINE_SLOTS = 6
ORIGINAL_ADR_VIEWER_POSITIVES = 4
ORIGINAL_ADR_VIEWER_ROUTINE_TASKS = 8


def hint_integrity(items: list[dict], expected_kind: str) -> tuple[int, int]:
    """Check receipts before treating deferrals as even *navigable* evidence."""
    seen_count = 0
    clipped_count = 0
    for entry in items:
        group = entry.get("weak_decision_hints")
        if group is None:
            continue
        if not isinstance(group, dict):
            raise ValueError("weak Decision hints are not an object")
        candidates = group.get("candidates")
        total, truncated = group.get("total_candidates"), group.get("truncated_candidates")
        if (
            not isinstance(candidates, list) or len(candidates) > 5
            or type(total) is not int or type(truncated) is not int
            or total < 0 or truncated < 0 or total != len(candidates) + truncated
        ):
            raise ValueError("weak Decision source-hint count or cap is invalid")
        selected = set(entry.get("source_verified_decisions", entry.get("current_decision_ids", [])))
        for item in candidates:
            if (
                not isinstance(item, dict) or not isinstance(item.get("id"), str)
                or not item["id"].startswith(expected_kind)
                or not isinstance(item.get("path"), str) or not item["path"]
                or not isinstance(item.get("sha256"), str)
                or re.fullmatch(r"[a-f0-9]{64}", item["sha256"]) is None
                or item["id"] in selected
            ):
                raise ValueError("weak Decision hint has unbound/selected/invalid identity")
        seen_count += len(candidates)
        clipped_count += truncated
    return seen_count, clipped_count


def privacyfence(report: dict) -> dict:
    scoring = report.get("developer_scoring")
    b = report.get("arms", {}).get("B_source_projection")
    if (
        report.get("engineering_gate") != "PASS"
        or report.get("source_repo") != "privacyfence/privacyfence"
        or report.get("source_sha") != PRIVACYFENCE_SHA
        or report.get("independent_holdout") is not False
        or report.get("real_agent_executed") is not False
        or report.get("owner_approval_authenticated") is not False
        or report.get("release_gate") != "HOLD"
        or report.get("tracked_upstream_clean") is not True
        or report.get("source_blobs_unchanged") is not True
        or not isinstance(scoring, dict)
        or not isinstance(b, list) or len(b) != 12
        or len({row.get("id") for row in b}) != 12
    ):
        raise ValueError("unverified, mutated or incomplete PrivacyFence receipt")
    target_count = scoring.get("developer_target_count")
    matched = scoring.get("B_current_decision_target_hits")
    negatives = [row for row in b if row.get("kind") == "routine-negative"]
    if len(negatives) != 2:
        raise ValueError("missing original PrivacyFence routine denominator")
    noise = sum(len(x.get("source_verified_decisions", [])) for x in negatives)
    hints, overflow = hint_integrity(b, "DEC-PF-")
    if target_count != ORIGINAL_PRIVACYFENCE_POSITIVES or matched != target_count:
        raise ValueError(
            f"missing PrivacyFence source-authorized target Decision: {matched}/{target_count}"
        )
    if (noise >= ORIGINAL_PRIVACYFENCE_ROUTINE_SLOTS
            or scoring.get("B_routine_cases_with_selected_decisions", 99) > 2):
        raise ValueError("PrivacyFence routine Decision noise did not improve")
    if not hints:
        raise ValueError("PrivacyFence default weak-hit deferral lacks source-bound hints")
    if any(
        row.get("schema_and_source_errors") or row.get("context_returncode")
        for row in b
    ):
        raise ValueError("PrivacyFence Context contains source/schema or CLI errors")
    return {
        "project": "privacyfence/privacyfence", "source_sha": PRIVACYFENCE_SHA,
        "developer_target_hits": matched,
        "developer_target_denominator": target_count,
        "baseline_routine_selected_decisions": ORIGINAL_PRIVACYFENCE_ROUTINE_SLOTS,
        "current_routine_selected_decisions": noise,
        "deferred_source_hints": hints,
        "omitted_visible_hints": overflow,
        "estimated_B_context_tokens": scoring.get("total_estimated_context_tokens", {}).get("B"),
        "agent_executed": False, "blind_holdout": False,
        "gate": "PASS",
    }


def adr_viewer(report: dict) -> dict:
    cases = report.get("cases")
    raw = report.get("raw_receipts", {})
    b = raw.get("B") if isinstance(raw, dict) else None
    if (
        report.get("engineering_gate") != "PASS"
        or report.get("source_repository") != "mrwilson/adr-viewer"
        or report.get("source_sha") != ADR_VIEWER_SHA
        or report.get("case_count") != 12
        or report.get("routine_cases") != 8
        or report.get("positive_target_decisions") != ORIGINAL_ADR_VIEWER_POSITIVES
        or report.get("real_agent_executed") is not False
        or report.get("independent_holdout") is not False
        or report.get("release_gate") != "HOLD"
        or report.get("upstream_source_unmodified") is not True
        or not isinstance(cases, list) or len(cases) != 12
        or not isinstance(b, list) or len(b) != 12
    ):
        raise ValueError("unverified, mutated or incomplete ADR Viewer receipt")
    hits = report.get("positive_target_hits")
    routine = report.get("routine_cases_with_extra_current_decisions")
    hint_receipts = [
        x.get("context", {}) if isinstance(x, dict) else {}
        for x in b
    ]
    hints, overflow = hint_integrity(hint_receipts, "DEC-ADR-")
    if hits != ORIGINAL_ADR_VIEWER_POSITIVES:
        raise ValueError(f"ADR Viewer lost original target Decisions: {hits}/4")
    if type(routine) is not int or routine >= ORIGINAL_ADR_VIEWER_ROUTINE_TASKS:
        raise ValueError(f"ADR Viewer routine noise has not improved: {routine}/8")
    if not hints:
        raise ValueError("ADR Viewer default deferral lacks source-bound hints")
    if any(entry.get("schema_errors") or entry.get("returncode")
           for entry in hint_receipts):
        raise ValueError("ADR Viewer has malformed Context source evidence")
    return {
        "project": "mrwilson/adr-viewer", "source_sha": ADR_VIEWER_SHA,
        "developer_target_hits": hits,
        "developer_target_denominator": ORIGINAL_ADR_VIEWER_POSITIVES,
        "baseline_routine_cases_with_current_decisions": ORIGINAL_ADR_VIEWER_ROUTINE_TASKS,
        "current_routine_cases_with_current_decisions": routine,
        "deferred_source_hints": hints,
        "omitted_visible_hints": overflow,
        "estimated_B_context_tokens": report.get("context_estimated_tokens_B_total"),
        "agent_executed": False, "blind_holdout": False,
        "gate": "PASS",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True, choices=["privacyfence", "adr-viewer"])
    p.add_argument("--input", type=pathlib.Path, required=True)
    args = p.parse_args()
    try:
        receipt = json.loads(args.input.read_text(encoding="utf-8"))
        result = privacyfence(receipt) if args.project == "privacyfence" else adr_viewer(receipt)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"default weak Decision regression gate FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
