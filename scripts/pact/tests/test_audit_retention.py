"""Review-only Decision retention inventory; never auto-archive knowledge."""

from __future__ import annotations

import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "pact"))
import audit
from discover import score_document


def decision(status: str, name: str) -> dict:
    return {
        "artifact_type": "decision",
        "status": status,
        "path": f".agents/decisions/{name}.md",
        "id": f"DEC-{name.upper().replace('-', '')}-001",
        "title": name,
        "text": "Retained durable rationale",
    }


class AuditRetentionTests(unittest.TestCase):

    def test_rejected_rationale_retrievable_without_permanent_prohibition(self) -> None:
        wrong = decision("rejected", "unsafe-cache")
        wrong["text"] = (
            "Rejected unbounded cache because prior storage was ephemeral. "
            "Revisit if durable storage and eviction are proven."
        )
        score, why = score_document(wrong, "unbounded cache")
        self.assertGreater(score, 0)
        self.assertNotIn("historical decision (not current guidance)", why)
        self.assertIn("Revisit if durable storage", wrong["text"])

        old = dict(wrong, status="superseded")
        old_score, old_why = score_document(old, "unbounded cache")
        self.assertLess(old_score, score)
        self.assertIn("historical decision (not current guidance)", old_why)

        exact_score, exact_why = score_document(old, old["id"])
        self.assertGreater(exact_score, old_score)
        self.assertNotIn("historical decision (not current guidance)", exact_why)

    def test_partial_and_full_supersession_are_review_only(self) -> None:
        old = decision("superseded", "partial-old")
        old["related"] = ["DEC-PARTIALNEW-001"]
        full = decision("superseded", "full-old")
        full["related"] = ["DEC-FULLNEW-001"]
        current = decision("implemented", "partial-new")
        rejected = decision("rejected", "old-idea")
        result = audit.evaluate(
            {"documents": [old, full, current, rejected]},
            deterministic_check="pass",
        )
        self.assertEqual(
            {item["id"] for item in result["decision_retention_candidates"]},
            {old["id"], full["id"]},
        )
        self.assertFalse("auto_delete" in result)
        self.assertFalse("auto_archive" in result)
        self.assertNotIn(
            current["id"],
            {item["id"] for item in result["decision_retention_candidates"]},
        )

    def test_only_explicitly_superseded_decisions_become_retention_candidates(self) -> None:
        implemented = decision("implemented", "current")
        superseded = decision("superseded", "old-boundary")
        archived = decision("archived", "historic")
        rejected = decision("rejected", "wrong-alternative")

        result = audit.evaluate(
            {"documents": [implemented, superseded, archived, rejected]},
            deterministic_check="pass",
        )
        self.assertEqual(result["deterministic_check"], "pass")
        self.assertEqual(
            [item["id"] for item in result["decision_retention_candidates"]],
            [superseded["id"]],
        )
        self.assertTrue(any(
            item["path"] == superseded["path"]
            for item in result["semantic_review_targets"]
        ))
        for item in result["decision_retention_candidates"]:
            self.assertIn("review", item["reason"])
            self.assertIn("do not archive automatically", item["reason"])
        self.assertNotIn(
            implemented["id"],
            [item["id"] for item in result["decision_retention_candidates"]],
        )

    def test_no_superseded_decisions_yields_no_retention_churn(self) -> None:
        result = audit.evaluate(
            {"documents": [decision("implemented", "active")]},
            deterministic_check="pass",
        )
        self.assertEqual(result["decision_retention_candidates"], [])
        self.assertEqual(result["semantic_review_targets"], [])

    def test_existing_active_change_and_drift_candidates_are_preserved(self) -> None:
        docs = [
            {
                "artifact_type": "change", "status": "active",
                "id": "CHANGE-1", "path": "docs/changes/active/one.md",
                "title": "Active work",
            },
            {
                "artifact_type": "drift", "status": "known",
                "id": "DRIFT-1", "path": "docs/drift/known/one.md",
                "title": "Known drift",
            },
            decision("superseded", "old-boundary"),
        ]
        result = audit.evaluate({"documents": docs}, deterministic_check="pass")
        self.assertEqual(len(result["active_changes"]), 1)
        self.assertEqual(len(result["known_drift"]), 1)
        self.assertEqual(len(result["decision_retention_candidates"]), 1)
        self.assertEqual(len(result["semantic_review_targets"]), 3)


if __name__ == "__main__":
    unittest.main()
