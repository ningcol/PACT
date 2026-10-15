"""Regression tests for safe, semantically incomplete task verification helpers."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
INIT = ROOT / "scripts" / "pact" / "init.py"


class TaskWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-task-workflow-")
        self.root = pathlib.Path(self.temp.name) / "project"
        self.root.mkdir()
        (self.root / "README.md").write_text("# Pilot project\n", encoding="utf-8")
        initialized = subprocess.run(
            [sys.executable, str(INIT), "--target", str(self.root), "--apply"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
        self.task_id = "TASK-VERIFY-1"
        prepared = self.pact(
            "task", "prepare", "Fix a narrow acceptance",
            "--task-id", self.task_id,
            "--success", "A specific observable outcome succeeds",
            "--accept", "Another independent outcome remains correct",
            "--risk", "medium", "--no-code", "--json",
        )
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def pact(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.root / "pact.py"), *args],
            cwd=self.root,
            text=True,
            capture_output=True,
        )

    @property
    def bundle(self) -> pathlib.Path:
        return self.root / ".pact" / "completions" / self.task_id

    def verify(self, *extra: str, exit_code: int = 0) -> subprocess.CompletedProcess[str]:
        return self.pact(
            "task", "verify", self.task_id,
            "--criterion", "AC-1",
            "--claim", "The targeted verification command exits successfully",
            "--json", *extra, "--",
            sys.executable, "-c", f"raise SystemExit({exit_code})",
        )


    def test_assist_is_read_only_and_never_reports_semantic_completion(self) -> None:
        self.assertEqual(self.pact("task", "draft", self.task_id).returncode, 0)
        paths = [self.bundle / name for name in
                 ("evidence.json", "convergence.json", "owner-report.json")]
        before = [item.read_bytes() for item in paths]
        result = self.pact("task", "assist", self.task_id, "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(set(report["unverified_criteria"]), {"AC-1", "AC-2"})
        self.assertTrue(report["requires_semantic_review"])
        self.assertFalse(report["owner_completed_automatically"])
        self.assertEqual(before, [item.read_bytes() for item in paths])
        self.assertNotEqual(self.pact("task", "finish", self.task_id).returncode, 0)

    def test_assist_fills_only_existing_pass_and_keeps_owner_partial(self) -> None:
        self.assertEqual(self.pact("task", "draft", self.task_id).returncode, 0)
        self.assertEqual(self.verify().returncode, 0)
        result = self.pact(
            "task", "assist", self.task_id, "--write-draft", "--json"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["draft_written"])
        self.assertEqual(report["unverified_criteria"], ["AC-2"])
        provenance = report["claim_provenance_for_review"]
        self.assertEqual(len(provenance), 1)
        self.assertEqual(provenance[0]["claim_id"], "EV-VERIFY-1")
        self.assertEqual(provenance[0]["criterion_ids"], ["AC-1"])
        self.assertEqual(provenance[0]["task_id"], self.task_id)
        self.assertRegex(provenance[0]["task_contract_sha256"], r"^[a-f0-9]{64}$")
        self.assertRegex(provenance[0]["task_context_sha256"], r"^[a-f0-9]{64}$")
        evidence = json.loads((self.bundle / "evidence.json").read_text())
        self.assertEqual(
            provenance[0]["run_receipt_refs"],
            [evidence["claims"][0]["evidence"][0]["ref"]],
        )
        owner_path = self.bundle / "owner-report.json"
        owner = json.loads(owner_path.read_text())
        self.assertEqual(owner["status"], "partial")
        self.assertEqual(owner["verification"], [{
            "claim": "The targeted verification command exits successfully",
            "evidence_ids": ["EV-VERIFY-1"],
        }])
        self.assertEqual(
            [item["criterion_id"] for item in owner.get("acceptance", [])],
            ["AC-1"],
        )
        saved = owner_path.read_bytes()
        again = self.pact(
            "task", "assist", self.task_id, "--write-draft", "--json"
        )
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertFalse(json.loads(again.stdout)["draft_written"])
        self.assertEqual(owner_path.read_bytes(), saved)
        self.assertNotEqual(self.pact("task", "finish", self.task_id).returncode, 0)

    def test_assist_reports_failed_and_missing_criteria_separately(self) -> None:
        self.assertEqual(self.pact("task", "draft", self.task_id).returncode, 0)
        self.assertEqual(self.verify(exit_code=7).returncode, 7)
        result = self.pact("task", "assist", self.task_id, "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        statuses = {
            item["criterion_id"]: item
            for item in report["criterion_diagnostics"]
        }
        self.assertEqual(statuses["AC-1"]["status"], "failed")
        self.assertEqual(statuses["AC-1"]["failed_claim_ids"], ["EV-VERIFY-1"])
        self.assertEqual(statuses["AC-2"]["status"], "unverified")
        self.assertEqual(statuses["AC-2"]["claim_ids"], [])
        self.assertEqual(report["failed_claim_ids"], ["EV-VERIFY-1"])
        self.assertFalse(report["owner_completed_automatically"])
        self.assertNotEqual(self.pact("task", "finish", self.task_id).returncode, 0)

    def test_pass_does_not_hide_another_required_fail_for_same_acceptance(self):
        self.assertEqual(self.pact("task", "draft", self.task_id).returncode, 0)
        self.assertEqual(self.verify(exit_code=7).returncode, 7)
        self.assertEqual(self.verify().returncode, 0)
        diagnostic = self.pact("task", "assist", self.task_id, "--json")
        self.assertEqual(diagnostic.returncode, 0, diagnostic.stdout + diagnostic.stderr)
        result = json.loads(diagnostic.stdout)
        ac1 = next(
            row for row in result["criterion_diagnostics"]
            if row["criterion_id"] == "AC-1"
        )
        self.assertEqual(ac1["status"], "failed")
        self.assertEqual(
            ac1["blocking_required_failed_claim_ids"], ["EV-VERIFY-1"]
        )
        self.assertNotIn(
            "AC-1",
            [row["criterion_id"] for row in result["safe_mechanical_acceptance"]],
        )
        drafted = self.pact(
            "task", "assist", self.task_id, "--write-draft", "--json"
        )
        self.assertEqual(drafted.returncode, 0, drafted.stdout + drafted.stderr)
        owner = json.loads((self.bundle / "owner-report.json").read_text())
        self.assertEqual(owner["status"], "partial")
        self.assertNotIn(
            "AC-1",
            [row["criterion_id"] for row in owner.get("acceptance", [])],
        )
        self.assertNotEqual(self.pact("task", "finish", self.task_id).returncode, 0)

    def test_assist_cannot_launder_failing_claim_into_owner_draft(self) -> None:
        self.assertEqual(self.pact("task", "draft", self.task_id).returncode, 0)
        self.assertEqual(self.verify(exit_code=3).returncode, 3)
        result = self.pact(
            "task", "assist", self.task_id, "--write-draft", "--json"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report["draft_written"])
        owner = json.loads((self.bundle / "owner-report.json").read_text())
        self.assertEqual(owner["verification"], [])
        self.assertEqual(owner["status"], "partial")

    def test_export_only_verified_metadata_and_refuses_escape_or_overwrite(self) -> None:
        self.assertEqual(self.verify().returncode, 0)
        attempt = self.pact(
            "task", "export", self.task_id,
            "--filename", "bundle-evidence.json", "--json"
        )
        self.assertEqual(attempt.returncode, 0, attempt.stdout + attempt.stderr)
        result = json.loads(attempt.stdout)
        output = self.root / result["output"]
        data = json.loads(output.read_text())
        self.assertFalse(data["completion_attestation"])
        self.assertEqual(data["task_id"], self.task_id)
        self.assertEqual(len(data["passing_execution_claims"]), 1)
        self.assertNotIn("argv", json.dumps(data))
        self.assertNotIn("stdout", json.dumps(data))
        duplicate = self.pact(
            "task", "export", self.task_id,
            "--filename", "bundle-evidence.json"
        )
        self.assertEqual(duplicate.returncode, 2)
        self.assertEqual(json.loads(output.read_text()), data)
        unsafe = self.pact(
            "task", "export", self.task_id,
            "--filename", "../outside.json"
        )
        self.assertEqual(unsafe.returncode, 2)
        self.assertFalse((self.root / ".pact" / "runs" / "outside.json").exists())

    def test_export_publication_failure_leaves_no_partial_final_file(self) -> None:
        self.assertEqual(self.verify().returncode, 0)
        runtime = self.root / ".pact" / "pact.pyz"
        script = (
            "import sys; from types import SimpleNamespace; "
            f"sys.path.insert(0, {str(runtime)!r}); "
            "import task_review; "
            "task_review.os.link = lambda *args, **kwargs: "
            "(_ for _ in ()).throw(OSError('injected link failure')); "
            f"raise SystemExit(task_review.export(SimpleNamespace(task_id={self.task_id!r}, "
            "filename='failed-export.json', json=True)))"
        )
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=self.root,
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        output_dir = self.root / ".pact" / "runs" / self.task_id
        self.assertFalse((output_dir / "failed-export.json").exists())
        self.assertFalse(list(output_dir.glob(".failed-export.json.pact-export-*.tmp")))

    def test_draft_is_schema_shaped_but_not_complete(self) -> None:
        drafted = self.pact("task", "draft", self.task_id, "--json")
        self.assertEqual(drafted.returncode, 0, drafted.stderr)
        self.assertEqual(
            set(json.loads(drafted.stdout)["created"]),
            {"evidence.json", "convergence.json", "owner-report.json"},
        )
        owner = json.loads((self.bundle / "owner-report.json").read_text())
        convergence = json.loads((self.bundle / "convergence.json").read_text())
        evidence = json.loads((self.bundle / "evidence.json").read_text())
        self.assertEqual(owner["status"], "partial")
        self.assertTrue(convergence["findings"])
        self.assertEqual(convergence["findings"][0]["classification"], "partial")
        self.assertEqual(evidence["claims"], [])
        finished = self.pact("task", "finish", self.task_id, "--json")
        self.assertNotEqual(finished.returncode, 0)

    def test_draft_is_idempotent_and_does_not_overwrite_review(self) -> None:
        self.assertEqual(self.pact("task", "draft", self.task_id).returncode, 0)
        path = self.bundle / "owner-report.json"
        owner = json.loads(path.read_text(encoding="utf-8"))
        owner["summary"] = "Human reviewed, not marked completed."
        path.write_text(json.dumps(owner), encoding="utf-8")
        result = self.pact("task", "draft", self.task_id, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["created"], [])
        self.assertEqual(json.loads(path.read_text())["summary"], owner["summary"])

    def test_verify_records_explicit_criterion_and_real_run_receipt(self) -> None:
        self.assertEqual(self.pact("task", "draft", self.task_id).returncode, 0)
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        evidence = json.loads((self.bundle / "evidence.json").read_text())
        self.assertEqual(summary["status"], "pass")
        self.assertEqual(evidence["claims"][0]["criteria"], ["AC-1"])
        self.assertEqual(evidence["claims"][0]["status"], "pass")
        receipt = self.root / evidence["claims"][0]["evidence"][0]["ref"]
        self.assertEqual(json.loads(receipt.read_text())["exit_code"], 0)
        self.assertEqual(
            json.loads((self.bundle / "owner-report.json").read_text())["status"],
            "partial",
        )
        # Explicitly verified AC-1 does not prove AC-2 or Convergence.
        self.assertNotEqual(self.pact("task", "finish", self.task_id).returncode, 0)

    def test_verify_failed_command_persists_failed_claim(self) -> None:
        result = self.verify(exit_code=7)
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
        data = json.loads((self.bundle / "evidence.json").read_text())
        self.assertEqual(data["claims"][0]["status"], "fail")
        self.assertNotEqual(self.pact("task", "finish", self.task_id).returncode, 0)

    def test_verify_can_append_without_losing_other_evidence(self) -> None:
        self.assertEqual(self.verify().returncode, 0)
        second = self.pact(
            "task", "verify", self.task_id, "--criterion", "AC-2",
            "--claim", "The independent check executed", "--",
            sys.executable, "-c", "print('ok')",
        )
        self.assertEqual(second.returncode, 0, second.stderr)
        evidence = json.loads((self.bundle / "evidence.json").read_text())
        self.assertEqual(
            [item["id"] for item in evidence["claims"]],
            ["EV-VERIFY-1", "EV-VERIFY-2"],
        )
        self.assertEqual(
            [item["criteria"] for item in evidence["claims"]],
            [["AC-1"], ["AC-2"]],
        )

    def test_unknown_criterion_blocks_before_command_execution(self) -> None:
        marker = self.root / "executed.txt"
        command = (
            "from pathlib import Path; "
            f"Path({str(marker)!r}).write_text('executed')"
        )
        result = self.pact(
            "task", "verify", self.task_id,
            "--criterion", "AC-NOPE", "--claim", "untrusted", "--",
            sys.executable, "-c", command,
        )
        self.assertEqual(result.returncode, 2)
        self.assertFalse(marker.exists())
        self.assertFalse((self.bundle / "evidence.json").exists())

    def test_changed_task_contract_blocks_before_execution(self) -> None:
        contract = self.root / ".pact" / "tasks" / self.task_id / "contract.json"
        contract.write_text(contract.read_text() + " ", encoding="utf-8")
        result = self.verify()
        self.assertEqual(result.returncode, 2)
        self.assertIn("stale prepared task", result.stderr)
        self.assertFalse((self.bundle / "evidence.json").exists())

    def test_external_completion_bundle_is_not_written(self) -> None:
        manifest_path = self.root / ".pact" / "tasks" / self.task_id / "task.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        target = pathlib.Path(self.temp.name) / "outside-bundle"
        manifest["completion_bundle"] = str(target)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        result = self.pact("task", "draft", self.task_id)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(target.exists())

    def test_duplicate_claim_id_is_refused_without_overwrite(self) -> None:
        self.assertEqual(self.verify("--claim-id", "EV-SAME").returncode, 0)
        old = (self.bundle / "evidence.json").read_bytes()
        second = self.verify("--claim-id", "EV-SAME")
        self.assertEqual(second.returncode, 2)
        self.assertEqual((self.bundle / "evidence.json").read_bytes(), old)

    def test_invalid_existing_evidence_blocks_scaffolding_and_verify(self) -> None:
        self.bundle.mkdir(parents=True)
        path = self.bundle / "evidence.json"
        path.write_text('{"corrupt": true}', encoding="utf-8")
        self.assertEqual(self.pact("task", "draft", self.task_id).returncode, 2)
        self.assertEqual(self.verify().returncode, 2)
        self.assertEqual(path.read_text(encoding="utf-8"), '{"corrupt": true}')


if __name__ == "__main__":
    unittest.main()
