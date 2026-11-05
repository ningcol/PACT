#!/usr/bin/env python3
"""Three-round, no-model knowledge-maintenance replay on a pinned real repository.

The *source* ADRs are real; task decisions and the Domain router are test-only
rehearsals inside an isolated GitHub Actions temporary clone. This is not an
independent Agent/Owner trial and cannot establish semantic obedience.
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
sys.path.insert(0, str(ROOT / "scripts" / "pact"))
from knowledge_retention import review as review_retention


DOMAIN_REL = "docs/product/domains/adr-styling.md"
DOMAIN_ID = "DOMAIN-ADR-STYLING"
CURRENT_DECISION = "DEC-ADR-0004"
HISTORICAL_DECISION = "DEC-ADR-0003"


def router_text(*, include_history: bool) -> str:
    """A test-only candidate navigation entry; NEVER claim confirmed truth."""
    related = [CURRENT_DECISION]
    if include_history:
        related.append(HISTORICAL_DECISION)
    return (
        "+++\n[pact]\ntype = \"domain\"\n"
        f"id = \"{DOMAIN_ID}\"\n"
        "status = \"candidate\"\n"
        "owners = [\"engineering\"]\n"
        f"related = {json.dumps(related)}\n"
        "aliases = []\npaths = []\n+++\n\n"
        "# ADR styling test navigation\n\n"
        "This is test-only routing of original public source ADRs, not "
        "authenticated product meaning.\n\n"
        f"## Current source-derived decision\n- {CURRENT_DECISION}\n"
        + (
            f"\n## Explicit historical source\n- {HISTORICAL_DECISION} "
            "(superseded; not current authority)\n"
            if include_history else ""
        )
    )


def invoke(target: pathlib.Path, *args: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(target / "pact.py"), *args],
        cwd=target, capture_output=True, text=True, timeout=120, check=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"pact {args[0]} failed ({result.returncode}): "
            + (result.stderr or result.stdout)[:1000]
        )
    if "--json" not in args:
        return {"returncode": result.returncode}
    payload = json.loads(result.stdout)
    if not isinstance(payload, dict):
        raise ValueError("PACT success payload must be an object")
    return payload


def observe(target: pathlib.Path, task_text: str, *, scope: bool) -> dict:
    audit_args = ["audit", "--json"]
    if scope:
        audit_args += ["--domain", DOMAIN_ID]
    audit = invoke(target, *audit_args)
    discovered = invoke(
        target, "discover", task_text, "--intent", "work", "--limit", "8", "--json"
    )
    sources = pilot.source_snapshot(target)
    domain_file = target / DOMAIN_REL
    return {
        "decision_files": sum(p.startswith(".agents/decisions/") for p in sources),
        "rule_files": sum(p.startswith("docs/product/rules/") for p in sources),
        "test_domain_files": int(domain_file.exists()),
        "deterministic_check": audit["deterministic_check"],
        "possible_overlaps": len(audit["possible_knowledge_overlaps"]),
        "alias_collisions": len(audit["domain_alias_collisions"]),
        "overlap_scan_truncated": audit["overlap_scan_truncated"],
        "retrieved_ids": [
            item.get("id") for item in discovered["results"] if item.get("id")
        ],
        "scoped_ids": [d["id"] for d in audit.get("scoped_sources", [])],
        "scoped_statuses": {
            d["id"]: d["status"] for d in audit.get("scoped_sources", [])
        },
    }


def retention(disposition: str, *, updated=None, created=None) -> dict:
    return {
        "knowledge_retention": {
            "disposition": disposition,
            "rationale": (
                "No new long-term record is warranted for a read-only review."
                if disposition == "none"
                else "Test-only source-derived router maintenance, no Owner approval."
            ),
            "updated": [] if updated is None else updated,
            "created": [] if created is None else created,
        }
    }


def run_replay(target: pathlib.Path, progress: dict) -> dict:
    cards = json.loads(pilot.CARDS.read_text(encoding="utf-8"))
    pilot.validate_frozen(cards, target)
    original_hashes = {
        d["source"]: m0.digest_file(target / d["source"])
        for d in cards["upstream_docs"]
    }
    progress["install"] = pilot.install_pact(target)
    projected = pilot.project_adrs(target, cards)
    base_snapshot = pilot.source_snapshot(target)
    if len(projected) != 6:
        raise ValueError("unexpected source-derived Decision projection count")

    query = cards["tasks"][1]["task"]  # frozen author-labelled maintenance question
    progress["stage"] = "T1: no durable knowledge change"
    t1 = observe(target, query, scope=False)
    problems, t1_review = review_retention(
        retention("none"), changed_files=[], require=True
    )
    if problems:
        raise ValueError("T1 review failed: " + "; ".join(problems))
    t1["retention"] = t1_review
    if pilot.source_snapshot(target) != base_snapshot:
        raise ValueError("T1 read-only review unexpectedly changed knowledge")

    progress["stage"] = "T2: create one candidate Domain router"
    domain_file = target / DOMAIN_REL
    domain_file.parent.mkdir(parents=True, exist_ok=True)
    if domain_file.exists():
        raise ValueError("test Domain already exists")
    domain_file.write_text(router_text(include_history=False), encoding="utf-8")
    problems, t2_review = review_retention(
        retention("create", created=[DOMAIN_REL]),
        changed_files=[DOMAIN_REL], require=True,
    )
    if problems:
        raise ValueError("T2 retention failed: " + "; ".join(problems))
    invoke(target, "check")
    t2 = observe(target, query, scope=True)
    t2["retention"] = t2_review

    progress["stage"] = "T3: update the same router with historical status"
    domain_file.write_text(router_text(include_history=True), encoding="utf-8")
    problems, t3_review = review_retention(
        retention("update", updated=[DOMAIN_REL]),
        changed_files=[DOMAIN_REL], require=True,
    )
    if problems:
        raise ValueError("T3 retention failed: " + "; ".join(problems))
    invoke(target, "check")
    t3 = observe(target, query, scope=True)
    t3["retention"] = t3_review

    source_clean = (
        not pilot.git_output(target, "status", "--porcelain", "--untracked-files=no")
        and all(
            m0.digest_file(target / path) == digest
            for path, digest in original_hashes.items()
        )
    )
    decisions_unchanged = (
        pilot.source_snapshot(target) == base_snapshot
    )
    status_preserved = (
        t3["scoped_statuses"].get(CURRENT_DECISION) == "implemented"
        and t3["scoped_statuses"].get(HISTORICAL_DECISION) == "superseded"
    )
    expected_counts = (
        [t1["decision_files"], t2["decision_files"], t3["decision_files"]]
        == [6, 6, 6]
        and [t1["test_domain_files"], t2["test_domain_files"], t3["test_domain_files"]]
        == [0, 1, 1]
    )
    problems = []
    if not source_clean:
        problems.append("original public repository tracked source was modified")
    if not decisions_unchanged:
        problems.append("test-only original-ADR Decision projections changed")
    if not status_preserved:
        problems.append("historical/current Decision status lost after maintenance")
    if not expected_counts:
        problems.append("unexpected durable knowledge growth across three rounds")
    if any(t["deterministic_check"] != "pass" for t in (t1, t2, t3)):
        problems.append("PACT deterministic audit did not pass")
    if any(t["overlap_scan_truncated"] for t in (t1, t2, t3)):
        problems.append("overlap candidate inventory incomplete")
    return {
        "version": 1,
        "kind": "pinned-real-repo / three no-model knowledge maintenance rounds",
        "source_repository": pilot.EXPECTED_UPSTREAM,
        "source_sha": pilot.EXPECTED_UPSTREAM_SHA,
        "tasks": [t1, t2, t3],
        "source_tracked_clean": source_clean,
        "source_adr_projection_unchanged": decisions_unchanged,
        "current_and_historical_status_preserved": status_preserved,
        "no_unnecessary_decision_growth": expected_counts,
        "new_confirmed_product_rules": 0,
        "candidate_domain_added": 1,
        "retrieval_improvement_proven": False,
        "semantic_conflict_detection_proven": False,
        "real_agent_executed": False,
        "owner_confirmation_observed": False,
        "agent_decision_obedience_verified": False,
        "long_term_effectiveness_proven": False,
        "engineering_gate": "PASS" if not problems else "FAIL",
        "gate_failures": problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    args = parser.parse_args()
    progress: dict = {}
    try:
        if os.environ.get("GITHUB_ACTIONS") != "true":
            raise ValueError("real-source pilot runs only in GitHub Actions isolation")
        target = pathlib.Path(args.target).resolve(strict=True)
        runner = pathlib.Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
        if target == runner or not target.is_relative_to(runner):
            raise ValueError("target must be a disposable clone within RUNNER_TEMP")
        result = run_replay(target, progress)
    except Exception as exc:
        result = {
            "version": 1,
            "engineering_gate": "FAIL",
            "gate_failures": [f"{type(exc).__name__}: {exc}"],
            "partial_progress": progress,
            "real_agent_executed": False,
            "agent_decision_obedience_verified": False,
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["engineering_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
