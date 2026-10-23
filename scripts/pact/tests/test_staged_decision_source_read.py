"""No-model downstream Decision source reading: verified bytes, never authority.

This measures counterfactual source exposure on pinned original-source pilots.
Reading a first document cannot prove complete semantic Decision coverage.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))
import decision_memory_m0 as m0


class StagedSourceReadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="pact-staged-source-")
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.first = self.source(
            ".agents/decisions/implemented/first.md",
            "# First\n\n## Decision\nPreserve the earlier contract.\n",
            "DEC-FIRST",
        )
        self.second = self.source(
            ".agents/decisions/implemented/second.md",
            "# Second\n\n## Decision\nNever omit this cross-domain constraint.\n",
            "DEC-SECOND",
        )
        self.past = self.source(
            ".agents/decisions/superseded/old.md",
            "# Old\n\n## Decision\nSuperseded history is not current authority.\n",
            "DEC-OLD",
        )

    def source(self, relative: str, content: str, ident: str) -> dict:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = content.encode("utf-8")
        path.write_bytes(raw)
        return {
            "id": ident, "artifact_type": "decision",
            "path": relative, "sha256": hashlib.sha256(raw).hexdigest(),
            "estimated_tokens": max((len(raw) + 3) // 4, 1),
        }

    def test_first_only_and_full_read_source_bytes_are_hash_verified(self):
        selected = [self.first, self.second, self.past]
        result = m0.staged_source_read_receipt(
            self.root, selected, ["DEC-SECOND", "DEC-FIRST"],
        )
        self.assertTrue(result["source_digest_verified"])
        self.assertEqual(
            result["selected_current_ids_in_context_order"],
            ["DEC-FIRST", "DEC-SECOND"],
        )
        self.assertEqual(result["first_only_id"], "DEC-FIRST")
        self.assertEqual(result["unread_in_first_only"], ["DEC-SECOND"])
        self.assertEqual(
            result["all_current_source_bytes"],
            self.first["estimated_tokens"] * 0
            + len((self.root / self.first["path"]).read_bytes())
            + len((self.root / self.second["path"]).read_bytes()),
        )
        self.assertEqual(
            result["first_only_source_bytes"],
            len((self.root / self.first["path"]).read_bytes()),
        )
        self.assertEqual(len(result["source_read_receipts"]), 2)
        self.assertEqual(result["model_calls"], 0)
        self.assertTrue(result["counterfactual_downstream_exposure_only"])

    def test_after_order_is_frozen_first_only_miss_blocks_default_claim(self):
        one = m0.staged_source_read_receipt(
            self.root, [self.first, self.second], ["DEC-FIRST", "DEC-SECOND"],
        )
        no_decision = m0.staged_source_read_receipt(self.root, [], [])
        data = m0.score_staged_source_reads(
            [{"id": "conflict", **one}, {"id": "routine", **no_decision}],
            {"conflict": ["DEC-SECOND"], "routine": []},
        )
        self.assertEqual(data["all_selected_primary_hits"], 1)
        self.assertEqual(data["first_only_primary_hits"], 0)
        self.assertEqual(data["author_labelled_primary_target_count"], 1)
        self.assertEqual(data["negative_case_count"], 1)
        self.assertEqual(data["first_only_default"], "NO-GO")
        self.assertEqual(data["release_gate"], "HOLD")
        self.assertFalse(data["real_agent_evidence"])
        self.assertGreater(data["counterfactual_exposure_bytes_difference"], 0)

    def test_verified_primary_hit_still_cannot_authorize_first_only(self):
        got = m0.staged_source_read_receipt(
            self.root, [self.first, self.second], ["DEC-FIRST", "DEC-SECOND"],
        )
        result = m0.score_staged_source_reads(
            [{"id": "conflict", **got}], {"conflict": ["DEC-FIRST"]},
        )
        self.assertEqual(result["first_only_primary_hits"], 1)
        self.assertEqual(result["all_selected_primary_hits"], 1)
        self.assertEqual(result["first_only_default"], "NO-GO")

    def test_empty_current_set_never_reads_superseded_source(self):
        record = m0.staged_source_read_receipt(self.root, [self.past], [])
        self.assertEqual(record["all_current_source_bytes"], 0)
        self.assertIsNone(record["first_only_id"])
        self.assertEqual(record["source_read_receipts"], [])

    def test_tampered_source_hash_and_cost_fail_closed(self):
        corrupted = {**self.first, "sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "changed after Context"):
            m0.staged_source_read_receipt(self.root, [corrupted], ["DEC-FIRST"])
        wrong_size = {**self.first, "estimated_tokens": 1_000_000}
        with self.assertRaisesRegex(ValueError, "estimate differs"):
            m0.staged_source_read_receipt(self.root, [wrong_size], ["DEC-FIRST"])
        with self.assertRaisesRegex(ValueError, "invalid"):
            m0.staged_source_read_receipt(self.root, [
                {**self.first, "sha256": "not-a-sha"},
            ], ["DEC-FIRST"])

    def test_duplicate_missing_and_unsafe_current_sources_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "identity or digest invalid"):
            m0.staged_source_read_receipt(
                self.root, [self.first, self.first], ["DEC-FIRST"],
            )
        with self.assertRaisesRegex(ValueError, "omitted a current"):
            m0.staged_source_read_receipt(
                self.root, [self.first], ["DEC-FIRST", "DEC-SECOND"],
            )
        with self.assertRaisesRegex(ValueError, "unsafe M0 path"):
            m0.staged_source_read_receipt(
                self.root, [{**self.first, "path": "../elsewhere"}], ["DEC-FIRST"],
            )
        with self.assertRaisesRegex(ValueError, "distinct current"):
            m0.staged_source_read_receipt(
                self.root, [self.first], ["DEC-FIRST", "DEC-FIRST"],
            )

    def test_grade_rejects_forged_candidate_order_and_denominator(self):
        r = m0.staged_source_read_receipt(
            self.root, [self.first], ["DEC-FIRST"],
        )
        with self.assertRaisesRegex(ValueError, "source order or integrity"):
            m0.score_staged_source_reads(
                [{"id": "a", **r, "first_only_id": "DEC-SECOND"}],
                {"a": ["DEC-FIRST"]},
            )
        with self.assertRaisesRegex(ValueError, "denominator"):
            m0.score_staged_source_reads(
                [{"id": "a", **r}], {"another": ["DEC-FIRST"]},
            )


if __name__ == "__main__":
    unittest.main()
