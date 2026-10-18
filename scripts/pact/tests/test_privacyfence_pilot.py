"""Frozen second real-repository benchmark: integrity before subjective metrics."""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))
import privacyfence_pilot as pilot


class PinnedPrivacyFenceTests(unittest.TestCase):
    def test_case_oracle_precommitted_source_sha(self):
        self.assertEqual(pilot.pilot.git_blob_sha(pilot.CASES), pilot.CASES_BLOB)
        self.assertEqual(pilot.pilot.git_blob_sha(pilot.ORACLE), pilot.ORACLE_BLOB)
        cards = json.loads(pilot.CASES.read_text(encoding="utf-8"))
        oracle = json.loads(pilot.ORACLE.read_text(encoding="utf-8"))
        self.assertEqual(cards["upstream_commit"], pilot.UPSTREAM_SHA)
        self.assertEqual(cards["pact_baseline"], pilot.PACT_BASE)
        self.assertEqual(len(cards["source_docs"]), 12)
        self.assertEqual(len(cards["tasks"]), 12)
        self.assertEqual(sum(d["status"] == "proposed"
                             for d in cards["source_docs"]), 1)
        self.assertEqual(sum(t["kind"] == "conflict" for t in cards["tasks"]), 10)
        self.assertEqual(sum(t["kind"] == "routine-negative" for t in cards["tasks"]), 2)
        self.assertEqual(set(oracle["expected_current"]),
                         {t["id"] for t in cards["tasks"]})
        for case in cards["tasks"]:
            self.assertNotIn("DEC-PF-", case["task"])
            self.assertNotIn("docs/adr/", case["task"])

    def test_relative_source_links_keep_original_meaning(self):
        text = (
            "# Original ADR\n"
            "Use [peer decision](0008-one-principal-per-os-user.md), "
            "[policy](../policy/README.md#topic), "
            "[web](https://example.org/a), [local](#part).\n"
        )
        modified = pilot.rebase_links(
            text, "docs/adr/0011-org-mode.md",
            ".agents/decisions/implemented/dec-pf-0011.md",
        )
        self.assertIn("../../../docs/adr/0008-one-principal-per-os-user.md", modified)
        self.assertIn("../../../docs/policy/README.md#topic", modified)
        self.assertIn("(https://example.org/a)", modified)
        self.assertIn("(#part)", modified)
        self.assertEqual(modified.count("# Original ADR"), 1)
        self.assertEqual(modified.count("peer decision"), 1)

    def test_source_metadata_is_status_faithful_and_minimal(self):
        with tempfile.TemporaryDirectory(prefix="pact-pf-fixture-") as td:
            root = pathlib.Path(td)
            docs = [
                {"id":"DEC-PF-0005", "source":"docs/adr/0005-sample.md",
                 "status":"proposed"},
                {"id":"DEC-PF-0013", "source":"docs/adr/0013-sample.md",
                 "status":"implemented"},
            ]
            for d in docs:
                path = root / d["source"]
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(
                    f"# Decision {d['id']}\n\n## Status\n\n"
                    + ("Proposed" if d["status"]=="proposed" else "Accepted")
                    + "\n\n## Decision\nKeep the source constraint.\n",
                    encoding="utf-8",
                )
            paths = pilot.project_sources(root,{"source_docs":docs})
            self.assertEqual(len(paths),2)
            for d in docs:
                relative = pilot.target_path(d)
                result = (root / relative).read_text(encoding="utf-8")
                self.assertIn('id = "'+d["id"]+'"',result)
                self.assertIn('status = "'+d["status"]+'"',result)
                self.assertIn("aliases = []",result)
                self.assertIn("domains = []",result)
                self.assertIn("paths = []",result)
                self.assertIn("Keep the source constraint.",result)
                self.assertEqual(paths[relative],pilot.m0.digest_file(root/relative))
                self.assertTrue((root/d["source"]).is_file())

    def test_unsupported_original_external_link_rejected(self):
        with self.assertRaisesRegex(ValueError,"exits upstream checkout"):
            pilot.rebase_links(
                "# Demo\n[unsafe](../../../external.md)",
                "docs/adr/original.md", ".agents/decisions/implemented/dec-pf-0001.md",
            )

    def test_missing_real_checkout_does_not_fake_success(self):
        with tempfile.TemporaryDirectory() as td:
            result=pilot.trial(pathlib.Path(td))
        self.assertEqual(result["engineering_gate"],"FAIL")
        self.assertEqual(result["release_gate"],"HOLD")
        self.assertFalse(result["real_agent_executed"])
        self.assertFalse(result["independent_holdout"])
        self.assertFalse(result["owner_approval_authenticated"])
        self.assertTrue(result["integrity_failures"])

    def test_source_target_path_does_not_allow_status_promotion(self):
        self.assertIn("/proposed/",
                      pilot.target_path({"id":"DEC-PF-0005","status":"proposed"}))
        self.assertIn("/implemented/",
                      pilot.target_path({"id":"DEC-PF-0013","status":"implemented"}))


if __name__ == "__main__":
    unittest.main()
