"""Frozen authored noise cases and scorer safety; not independent Agent trials."""
from __future__ import annotations

import json
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))
import decision_memory_noise_probe as probe


class PinnedBrownfieldNoiseTests(unittest.TestCase):
    def cases(self):
        return probe.load_frozen_cases()

    def test_frozen_git_blobs_and_nonblind_denominator(self):
        cases = self.cases()
        self.assertEqual(probe.pilot.git_blob_sha(probe.CASES), probe.CASES_BLOB)
        self.assertEqual(probe.pilot.git_blob_sha(probe.ORACLE), probe.ORACLE_BLOB)
        self.assertEqual(cases["pact_source_baseline"], probe.FROZEN_PACT_BASELINE)
        self.assertEqual(len(cases["cases"]), 12)
        self.assertEqual(
            sum(x["type"] == "routine-negative" for x in cases["cases"]), 8
        )
        oracle = probe.load_frozen_oracle(cases)
        self.assertEqual(
            set(oracle["expected_current"]),
            {item["id"] for item in cases["cases"]},
        )
        self.assertEqual(
            sum(bool(ids) for ids in oracle["expected_current"].values()), 4
        )
        self.assertFalse(oracle["first_evaluation_unobserved"] is False)

    def test_scored_report_declares_historical_status_and_actual_agent_unknown(self):
        cases = self.cases()
        oracle = probe.load_frozen_oracle(cases)
        source = json.loads(probe.pilot.CARDS.read_text(encoding="utf-8"))
        positive = [x for x in cases["cases"] if x["type"] == "decision-conflict"]
        self.assertEqual(len(positive), 4)
        allowed = {d["id"]: d["status"] for d in source["upstream_docs"]}
        for case in positive:
            for ident in oracle["expected_current"][case["id"]]:
                self.assertEqual(allowed.get(ident), "implemented")
        self.assertEqual(allowed["DEC-ADR-0003"], "superseded")
        self.assertEqual(cases["settings"]["code_context"], False)
        self.assertEqual(cases["settings"]["estimated_token_budget"], 2048)

    def test_no_id_in_freeze_and_no_fabricated_oracle_session(self):
        cases = self.cases()
        self.assertTrue(all(
            "DEC-ADR-" not in card["task"] for card in cases["cases"]
        ))
        self.assertEqual(
            cases["external_sha"], probe.pilot.EXPECTED_UPSTREAM_SHA
        )

    def test_safety_gate_requires_decision_source_and_empty_raw_adr_authority(self):
        cases = self.cases()
        oracle = probe.load_frozen_oracle(cases)
        source = json.loads(probe.pilot.CARDS.read_text(encoding="utf-8"))
        paths = probe.pilot.projected_decision_paths(source)
        digests = {path: ("e" * 64) for path in paths.values()}

        def context_record(case_id, ids):
            selected = [
                {"id": ident, "path": paths[ident],
                 "artifact_type": "decision", "sha256": digests[paths[ident]]}
                for ident in ids
            ]
            return {
                "id": case_id,
                "discovery": {"returncode": 0, "schema_errors": [], "hits": []},
                "context": {
                    "returncode": 0, "schema_errors": [],
                    "status": "candidate", "code_context_selected": 0,
                    "current_decision_ids": list(ids),
                    "selected_artifacts": selected,
                    "selected_knowledge_files": len(selected),
                    "estimated_selected_tokens": 150,
                },
            }

        a = [context_record(t["id"], []) for t in cases["cases"]]
        b = [
            context_record(t["id"], oracle["expected_current"][t["id"]])
            for t in cases["cases"]
        ]
        evidence = {
            "A": a, "B": b,
            "A_scored": [{"id": x["id"], "hits": []} for x in a],
            "B_scored": [{"id": x["id"], "hits": []} for x in b],
            "knowledge_expected": digests, "knowledge_after": dict(digests),
            "original_adrs_unmodified": True,
            "pact_check": {"returncode": 0},
            "install": {
                "installed_source_match": True,
                "source_checkout_git_sha": probe.FROZEN_PACT_BASELINE,
                "installed_archive_sha256": "a" * 64,
            },
        }
        clean = probe.score(evidence, cases, oracle)
        self.assertEqual(clean["engineering_gate"], "PASS", clean["gate_failures"])
        self.assertEqual(clean["positive_target_hits"], 4)
        self.assertEqual(clean["routine_cases_with_extra_current_decisions"], 0)
        self.assertFalse(clean["real_agent_executed"])

        # Forge an expected current ID without actually selecting its source.
        first = next(i for i, t in enumerate(cases["cases"])
                     if oracle["expected_current"][t["id"]])
        removed = evidence["B"][first]["context"]["selected_artifacts"].pop()
        corrupted = probe.score(evidence, cases, oracle)
        self.assertEqual(corrupted["engineering_gate"], "FAIL")
        self.assertTrue(any("no matching selected source/digest" in issue
                            for issue in corrupted["gate_failures"]))
        evidence["B"][first]["context"]["selected_artifacts"].append(removed)

        # Raw upstream ADRs must never be assigned PACT Decision authority.
        evidence["A"][0]["context"]["current_decision_ids"] = ["DEC-ADR-0001"]
        wrong = probe.score(evidence, cases, oracle)
        self.assertEqual(wrong["engineering_gate"], "FAIL")
        self.assertTrue(any("unadapted original ADRs promoted" in issue
                            for issue in wrong["gate_failures"]))

    def test_score_marks_fabricated_routine_decision_as_quality_hold(self):
        cases = self.cases()
        oracle = probe.load_frozen_oracle(cases)
        known = [
            d["id"] for d in json.loads(probe.pilot.CARDS.read_text(
                encoding="utf-8"
            ))["upstream_docs"] if d["status"] == "implemented"
        ]
        a, b = [], []
        for case in cases["cases"]:
            packet = {
                "id": case["id"],
                "discovery": {"returncode": 0, "schema_errors": [], "hits": []},
                "context": {
                    "returncode": 0, "schema_errors": [],
                    "status": "candidate", "code_context_selected": 0,
                    "current_decision_ids": [],
                    "selected_knowledge_files": 0,
                    "estimated_selected_tokens": 100,
                },
            }
            a.append({**packet, "context": dict(packet["context"])})
            guess = oracle["expected_current"][case["id"]].copy()
            if case["id"] == "format-server-imports":
                guess = [known[0]]  # One unexpected, explicitly negative task
            b.append({**packet, "context": {
                **packet["context"], "current_decision_ids": guess,
                "selected_knowledge_files": len(guess),
            }})
        evidence = {
            "A": a, "B": b,
            "A_scored": [{"id": x["id"], "hits": []} for x in a],
            "B_scored": [{"id": x["id"], "hits": []} for x in b],
            "knowledge_expected": {"a": "digest"},
            "knowledge_after": {"a": "digest", "b": "added"},
            "original_adrs_unmodified": True,
            "pact_check": {"returncode": 0},
            "install": {"installed_source_match": True,
                        "installed_archive_sha256": "a" * 64,
                        "source_checkout_git_sha": probe.FROZEN_PACT_BASELINE},
        }
        scored = probe.score(evidence, cases, oracle)
        self.assertEqual(scored["retrieval_quality"], "HOLD")
        self.assertEqual(scored["routine_cases_with_extra_current_decisions"], 1)
        self.assertEqual(scored["engineering_gate"], "FAIL")
        self.assertFalse(scored["real_agent_executed"])
        self.assertFalse(scored["independent_holdout"])
        self.assertEqual(scored["release_gate"], "HOLD")


if __name__ == "__main__":
    unittest.main()
