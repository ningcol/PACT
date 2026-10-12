"""PR-01 regression tests for prepared contracts and acceptance trust."""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

RUNTIME = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNTIME))

import task
import task_contract
import report


def contract_and_reports():
    contract = {
        "version": 1, "task_id": "TASK-PR01", "intent": "Preserve the outcome",
        "acceptance_criteria": [{"id": "AC-1", "kind": "outcome", "text": "Correct outcome"}],
    }
    evidence = {
        "version": 1, "task_id": "TASK-PR01", "task": "Preserve the outcome",
        "risk_level": "medium", "limitations": [],
        "claims": [{"id": "EV-ONE", "claim": "Confirmed result", "required": True,
                    "status": "pass", "criteria": ["AC-1"], "evidence": []}],
    }
    owner = {
        "version": 1, "task_id": "TASK-PR01", "status": "completed",
        "summary": "Complete", "before": "Before", "after": "After",
        "verification": [{"claim": "Confirmed result", "evidence_ids": ["EV-ONE"]}],
        "acceptance": [{"criterion_id": "AC-1", "summary": "Correct outcome",
                        "evidence_ids": ["EV-ONE"]}],
        "consistency": {"status": "aligned", "summary": "Aligned"}, "owner_decisions": [],
    }
    return contract, evidence, owner


class PR01TrustRegressionTests(unittest.TestCase):
    def test_optional_passing_claim_cannot_satisfy_acceptance(self):
        contract, evidence, owner = contract_and_reports()
        evidence["claims"][0]["required"] = False
        errors, stats = task_contract.acceptance_review(contract, evidence, owner)
        self.assertTrue(any("AC-1" in error for error in errors), errors)
        self.assertEqual(stats["evidence_verified"], 0)

    def test_required_passing_claim_still_satisfies_acceptance(self):
        contract, evidence, owner = contract_and_reports()
        errors, stats = task_contract.acceptance_review(contract, evidence, owner)
        self.assertEqual(errors, [])
        self.assertEqual(stats["owner_report_covered"], 1)

    def test_extra_owner_acceptance_is_rejected(self):
        contract, evidence, owner = contract_and_reports()
        owner["acceptance"].append({
            "criterion_id": "AC-EXTRA", "summary": "Unrequested outcome",
            "evidence_ids": ["EV-ONE"],
        })
        errors, _ = task_contract.acceptance_review(contract, evidence, owner)
        self.assertTrue(any("AC-EXTRA" in error for error in errors), errors)

    def test_acceptance_rejects_unrelated_or_unknown_evidence_ids(self):
        contract, evidence, owner = contract_and_reports()
        evidence["claims"].append({
            "id": "EV-OTHER", "claim": "Another criterion",
            "required": True, "status": "pass", "criteria": [],
            "evidence": [],
        })
        owner["acceptance"][0]["evidence_ids"] = ["EV-ONE", "EV-OTHER", "EV-MISSING"]
        errors, stats = task_contract.acceptance_review(contract, evidence, owner)
        self.assertTrue(any("EV-OTHER" in error for error in errors), errors)
        self.assertTrue(any("EV-MISSING" in error for error in errors), errors)
        self.assertEqual(stats["owner_report_covered"], 0)

    def test_duplicate_claim_ids_are_rejected(self):
        _, evidence, owner = contract_and_reports()
        evidence["claims"].append({
            "id": "EV-ONE", "claim": "Conflicting result",
            "required": False, "status": "unverified", "evidence": [],
        })
        errors = report.cross_validate(owner, evidence, {"task_id": "TASK-PR01", "findings": []},
                                       validate_provenance=False)
        self.assertTrue(any("duplicate" in error.lower() for error in errors), errors)

    def test_prepared_contract_hash_cannot_be_rewritten(self):
        contract, _, _ = contract_and_reports()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            path = root / "contract.json"
            path.write_text(json.dumps(contract), encoding="utf-8")
            old_sha = hashlib.sha256(path.read_bytes()).hexdigest()
            contract["acceptance_criteria"][0]["text"] = "Weaker outcome"
            path.write_text(json.dumps(contract), encoding="utf-8")
            manifest = {
                "contract_sha256": old_sha,
                "contract": "contract.json",
                "context": "context.json",
                "context_sha256": "a" * 64,
                "risk_level": "low",
                "workspace_baseline": {"kind": "filesystem", "workspace_sha256": "a" * 64},
            }
            errors = task.validate_finish_manifest(manifest, root=root)
            self.assertTrue(any("contract_sha256" in err for err in errors), errors)

    def test_contract_mutation_rejected_before_task_state_writes(self):
        contract, _, _ = contract_and_reports()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            task_root = root / ".pact" / "tasks"
            task_dir = task_root / "TASK-PR01"
            task_dir.mkdir(parents=True)
            contract_path = task_dir / "contract.json"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            old_sha = hashlib.sha256(contract_path.read_bytes()).hexdigest()
            contract["acceptance_criteria"][0]["text"] = "Weaker outcome"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            manifest = {
                "task_id": "TASK-PR01", "contract": ".pact/tasks/TASK-PR01/contract.json",
                "contract_sha256": old_sha, "context": ".pact/tasks/TASK-PR01/context.json",
                "context_sha256": "a" * 64, "risk_level": "low",
                "workspace_baseline": {"kind": "filesystem", "workspace_sha256": "a" * 64},
            }
            manifest_path = task_dir / "task.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with mock.patch.object(task, "ROOT", root), \
                 mock.patch.object(task, "TASK_ROOT", task_root), \
                 mock.patch.object(task, "COMPLETION_ROOT", root / ".pact" / "completions"), \
                 mock.patch.object(task, "task_changed_files", side_effect=AssertionError("premature side effect")):
                rc = task.finish(type("Args", (), {"task_id": "TASK-PR01", "bundle": None,
                                                   "require_ci_metadata": False, "json": True})())
            self.assertEqual(rc, 2)
            self.assertFalse((task_dir / "final-impact.json").exists())
            self.assertFalse((task_dir / "completion-attempts.jsonl").exists())
            self.assertEqual(json.loads(manifest_path.read_text())["task_id"], "TASK-PR01")


if __name__ == "__main__":
    unittest.main()
