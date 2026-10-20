"""No-model, frozen-denominator default weak retrieval gate regression tests."""
from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))
import default_weak_decision_gate as gate


def hint(ident: str) -> dict:
    return {
        "id": ident, "path": f".agents/decisions/implemented/{ident.lower()}.md",
        "sha256": "a" * 64,
    }


def privacy_receipt() -> dict:
    records = []
    for n in range(10):
        records.append({
            "id": f"conflict-{n}", "kind": "conflict",
            "source_verified_decisions": [f"DEC-PF-1{n:03d}"],
            "schema_and_source_errors": [], "context_returncode": 0,
        })
    records.extend([
        {
            "id": "docs-whitespace", "kind": "routine-negative",
            "source_verified_decisions": [],
            "weak_decision_hints": {
                "total_candidates": 2, "truncated_candidates": 0,
                "candidates": [hint("DEC-PF-0008"), hint("DEC-PF-0014")],
            },
            "schema_and_source_errors": [], "context_returncode": 0,
        },
        {
            "id": "test-variable", "kind": "routine-negative",
            "source_verified_decisions": ["DEC-PF-0155"],
            "weak_decision_hints": {
                "total_candidates": 2, "truncated_candidates": 0,
                "candidates": [hint("DEC-PF-0008"), hint("DEC-PF-0014")],
            },
            "schema_and_source_errors": [], "context_returncode": 0,
        },
    ])
    return {
        "engineering_gate": "PASS",
        "source_repo": "privacyfence/privacyfence",
        "source_sha": gate.PRIVACYFENCE_SHA,
        "independent_holdout": False, "real_agent_executed": False,
        "owner_approval_authenticated": False, "release_gate": "HOLD",
        "tracked_upstream_clean": True, "source_blobs_unchanged": True,
        "developer_scoring": {
            "developer_target_count": 10,
            "B_current_decision_target_hits": 10,
            "B_routine_cases_with_selected_decisions": 1,
            "total_estimated_context_tokens": {"A": 0, "B": 30000},
        },
        "arms": {"B_source_projection": records},
    }


def adr_receipt() -> dict:
    records = [
        {"id": f"routine-{i}", "context": {
            "returncode": 0, "schema_errors": [],
            "current_decision_ids": [],
            **({"weak_decision_hints": {
                "total_candidates": 1, "truncated_candidates": 0,
                "candidates": [hint("DEC-ADR-0002")],
            }} if i == 0 else {}),
        }} for i in range(8)
    ]
    records.extend([
        {"id": f"positive-{i}", "context": {
            "returncode": 0, "schema_errors": [],
            "current_decision_ids": [f"DEC-ADR-000{i + 1}"],
        }} for i in range(4)
    ])
    return {
        "engineering_gate": "PASS",
        "source_repository": "mrwilson/adr-viewer",
        "source_sha": gate.ADR_VIEWER_SHA,
        "case_count": 12, "routine_cases": 8,
        "positive_target_decisions": 4, "positive_target_hits": 4,
        "routine_cases_with_extra_current_decisions": 3,
        "real_agent_executed": False, "independent_holdout": False,
        "release_gate": "HOLD", "upstream_source_unmodified": True,
        "context_estimated_tokens_B_total": 7000,
        "cases": [{"id": f"c{i}"} for i in range(12)],
        "raw_receipts": {"B": records},
    }


class DefaultWeakGateTests(unittest.TestCase):
    def test_privacyfence_positive_required_and_reduces_noise(self):
        self.assertEqual(gate.privacyfence(privacy_receipt())["gate"], "PASS")
        missing = privacy_receipt()
        missing["developer_scoring"]["B_current_decision_target_hits"] = 9
        with self.assertRaisesRegex(ValueError, "missing PrivacyFence"):
            gate.privacyfence(missing)
        noisy = privacy_receipt()
        noisy["arms"]["B_source_projection"][-1]["source_verified_decisions"] = [
            f"DEC-PF-{i:04d}" for i in range(6)
        ]
        with self.assertRaisesRegex(ValueError, "noise did not improve"):
            gate.privacyfence(noisy)

    def test_privacyfence_oracle_and_source_compromise_fail_closed(self):
        invalid = privacy_receipt()
        invalid["owner_approval_authenticated"] = True
        with self.assertRaisesRegex(ValueError, "unverified"):
            gate.privacyfence(invalid)
        invalid = privacy_receipt()
        invalid["arms"]["B_source_projection"][-1]["schema_and_source_errors"] = [
            "deferred source missing"
        ]
        with self.assertRaisesRegex(ValueError, "source/schema"):
            gate.privacyfence(invalid)

    def test_adr_frozen_positive_and_negative_gate(self):
        self.assertEqual(gate.adr_viewer(adr_receipt())["gate"], "PASS")
        missing = adr_receipt()
        missing["positive_target_hits"] = 3
        with self.assertRaisesRegex(ValueError, "lost original target"):
            gate.adr_viewer(missing)
        noisy = adr_receipt()
        noisy["routine_cases_with_extra_current_decisions"] = 8
        with self.assertRaisesRegex(ValueError, "has not improved"):
            gate.adr_viewer(noisy)

    def test_deferred_hints_cannot_be_copied_selected_or_forged(self):
        packet = privacy_receipt()
        packet["arms"]["B_source_projection"][-2]["source_verified_decisions"] = ["DEC-PF-0008"]
        with self.assertRaisesRegex(ValueError, "unbound/selected"):
            gate.privacyfence(packet)
        packet = privacy_receipt()
        packet["arms"]["B_source_projection"][-2]["weak_decision_hints"]["candidates"][0][
            "sha256"
        ] = "Z" * 64
        with self.assertRaisesRegex(ValueError, "unbound/selected"):
            gate.privacyfence(packet)
        packet = privacy_receipt()
        packet["arms"]["B_source_projection"][-2]["weak_decision_hints"][
            "truncated_candidates"
        ] = 3
        with self.assertRaisesRegex(ValueError, "count"):
            gate.privacyfence(packet)


if __name__ == "__main__":
    unittest.main()
