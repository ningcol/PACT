"""Advisory metadata is not semantic approval or a second AC namespace."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from task_review import _diagnose


class CompletionAdvisoryDetailsTests(unittest.TestCase):
    def test_missing_coverage_labels_and_failed_evidence_remain_advisory(self):
        manifest = {"task_id": "TASK-X", "status": "prepared", "risk_level": "low",
                    "contract_sha256": "a" * 64, "context_sha256": "b" * 64}
        contract = {"acceptance_criteria": [
            {"id": "AC-1", "text": "AC-9a： Preserve content", "kind": "outcome"}]}
        context = {"artifacts": [{"path": "docs/example.md"}]}
        evidence = {"claims": [{"id": "EV-FAIL", "status": "fail", "required": True,
                                 "criteria": ["AC-1"], "claim": "Record check failed",
                                 "evidence": [{"kind": "manual", "provenance": "manual",
                                               "ref": "original review"}]}]}
        report = _diagnose(manifest, contract, context, evidence, None, None,
                           {"supported": True, "changed_files": ["app.py"]}, [], [])
        self.assertEqual(report["criterion_label_warnings"][0]["body_label"], "AC-9a")
        self.assertEqual(report["coverage_review_draft"]["changes"],
                         [{"path": "app.py", "review_required": True}])
        self.assertNotIn("disposition", report["coverage_review_draft"]["context"][0])
        self.assertEqual(report["criterion_evidence_trace"][0]["claim_ids"], ["EV-FAIL"])
        self.assertEqual(report["evidence_trace_claims"][0]["status"], "fail")
        self.assertFalse(report["evidence_trace_truncated"])
        self.assertEqual(report["safe_mechanical_acceptance"], [])
        self.assertFalse(report["owner_completed_automatically"])
        self.assertEqual(contract["acceptance_criteria"][0]["text"], "AC-9a： Preserve content")
        evidence["claims"][0]["claim"] = "x" * 2000
        evidence["claims"][0]["evidence"] *= 30
        contract["acceptance_criteria"] *= 60
        bounded = _diagnose(manifest, contract, context, evidence, None, None,
                            {"supported": True, "changed_files": []}, [], [])
        self.assertTrue(bounded["evidence_trace_truncated"])
        self.assertEqual(len(bounded["evidence_trace_claims"]), 1)
        self.assertEqual(len(bounded["evidence_trace_claims"][0]["claim"]), 512)
        self.assertEqual(len(bounded["evidence_trace_claims"][0]["references"]), 10)
        self.assertEqual(len(bounded["criterion_evidence_trace"]), 50)
