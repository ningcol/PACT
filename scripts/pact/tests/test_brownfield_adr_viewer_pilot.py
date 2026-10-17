"""Check frozen real-GitHub-source pilot boundaries without network or Agent claims."""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))
import brownfield_adr_viewer as pilot


class BrownfieldAdrViewerPilotTests(unittest.TestCase):
    @staticmethod
    def fixture():
        return json.loads(pilot.CARDS.read_text(encoding="utf-8"))

    def test_frozen_github_repository_and_oracle_integrity(self):
        cards = self.fixture()
        oracle = json.loads(pilot.ORACLE.read_text(encoding="utf-8"))
        self.assertEqual(pilot.git_blob_sha(pilot.CARDS), pilot.CARDS_BLOB)
        self.assertEqual(pilot.git_blob_sha(pilot.ORACLE), pilot.ORACLE_BLOB)
        self.assertEqual(cards["upstream"], "mrwilson/adr-viewer")
        self.assertEqual(cards["upstream_commit"], pilot.EXPECTED_UPSTREAM_SHA)
        self.assertEqual(cards["pact_parent_sha"], pilot.EXPECTED_BASELINE_SHA)
        self.assertEqual(len(cards["upstream_docs"]), 6)
        self.assertEqual(len(cards["tasks"]), 6)
        self.assertEqual(set(oracle["expected_current"]),
                         {c["id"] for c in cards["tasks"]})
        self.assertEqual(sum(bool(v) for v in oracle["expected_current"].values()), 4)
        for card in cards["tasks"]:
            self.assertNotIn("DEC-ADR-", card["task"])
        self.assertEqual(cards["settings"]["knowledge_limit"], 4)

    def test_copy_original_source_rationale_without_invented_anchors(self):
        cards = self.fixture()
        upstream = (
            "# 4. Distinguish superseded records with colour\n\n"
            "## Status\n\nAccepted\n\n## Context\n\nDifferent states\n\n"
            "## Decision\n\nUse distinct styling.\n"
        )
        md = pilot.render_adapted_original(cards["upstream_docs"][3], upstream)
        self.assertIn('id = "DEC-ADR-0004"', md)
        self.assertIn('status = "implemented"', md)
        self.assertIn('supersedes = ["DEC-ADR-0003"]', md)
        self.assertIn("Use distinct styling.", md)
        self.assertIn("Test-only projection", md)
        self.assertIn("aliases = []", md)
        self.assertIn("paths = []", md)
        self.assertNotIn('status = "confirmed"', md)

    def test_reject_invented_or_tampered_source_status(self):
        original = self.fixture()["upstream_docs"][3]
        with self.assertRaisesRegex(ValueError, "upgrade"):
            pilot.render_adapted_original(original, "# ADR\n\n## Status\n\nRejected\n")
        with self.assertRaisesRegex(ValueError, "missing title"):
            pilot.render_adapted_original(original, "## Status\n\nAccepted\n")
        old = self.fixture()["upstream_docs"][2]
        with self.assertRaisesRegex(ValueError, "non-superseded"):
            pilot.render_adapted_original(old, "# Old\n\n## Status\n\nAccepted\n")

    def test_status_lineage_does_not_confuse_amended_with_superseded(self):
        cards = self.fixture()
        decisions = {d["id"]: d for d in cards["upstream_docs"]}
        self.assertEqual(decisions["DEC-ADR-0003"]["status"], "superseded")
        self.assertEqual(decisions["DEC-ADR-0003"]["superseded_by"],
                         "DEC-ADR-0004")
        self.assertEqual(decisions["DEC-ADR-0004"]["supersedes"],
                         ["DEC-ADR-0003"])
        self.assertNotIn("supersedes", decisions["DEC-ADR-0005"])

    def test_document_scope_includes_added_non_markdown_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = pathlib.Path(tmp)
            folder = target / ".agents" / "decisions" / "implemented"
            folder.mkdir(parents=True)
            (folder / "temp.md").write_text("# fake", encoding="utf-8")
            baseline = pilot.source_snapshot(target)
            (folder / "extra.json").write_text("{}", encoding="utf-8")
            self.assertEqual(len(pilot.source_snapshot(target)), len(baseline) + 1)

    def test_scoring_fails_closed_if_source_or_history_changed(self):
        cards = self.fixture()
        oracle = json.loads(pilot.ORACLE.read_text(encoding="utf-8"))
        def packet(cid, expected):
            return {
                "id": cid,
                "discovery": {"returncode": 0, "hits": []},
                "context": {
                    "returncode": 0, "status": "candidate",
                    "current_decision_ids": list(expected),
                    "selected_ids": list(expected),
                    "applicable_rule_ids": [],
                    "selected_knowledge_files": len(expected),
                    "code_context_selected": 0,
                    "estimated_selected_tokens": 24,
                    "elapsed_ms": 1,
                },
            }
        original = [packet(c["id"], []) for c in cards["tasks"]]
        adapted = [
            packet(c["id"], oracle["expected_current"][c["id"]])
            for c in cards["tasks"]
        ]
        adapted[0]["context"]["current_decision_ids"] = ["DEC-ADR-0003"]
        adapted[0]["context"]["selected_ids"] = ["DEC-ADR-0003"]
        evidence = {
            "A_plain_legacy": original, "B_adapted": adapted,
            "unmodified_tracked_sources": False,
            "projected_paths": list(range(6)),
            "project_check_returncode": 0,
            "knowledge_expected": {"doc": "sha"}, "knowledge_after": {"doc": "sha"},
            "install": {},
        }
        result = pilot.score(evidence, cards, oracle)
        self.assertEqual(result["engineering_safety_gate"], "FAIL")
        self.assertTrue(any("tracked files changed" in err
                            for err in result["safety_gate_failures"]))
        self.assertTrue(any("historical" in err for err in result["safety_gate_failures"]))
        self.assertFalse(result["real_agent_executed"])
        self.assertFalse(result["owner_approval_authenticated"])
        self.assertEqual(result["release_gate"], "HOLD")
        del evidence["B_adapted"][0]
        with self.assertRaisesRegex(ValueError, "missing raw predictions"):
            pilot.score(evidence, cards, oracle)


if __name__ == "__main__":
    unittest.main()
