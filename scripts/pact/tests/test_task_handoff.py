"""S5: process-separated checkpoint/recovery does not trust Agent narration."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


SOURCE = pathlib.Path(__file__).resolve().parents[3]
INIT = SOURCE / "scripts" / "pact" / "init.py"


class TaskHandoffIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pact-handoff-")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name) / "project"
        self.root.mkdir()
        (self.root / "README.md").write_text("initial content\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(INIT), "--target", str(self.root), "--apply"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        for cmd in (
            ["git", "init", "-q"],
            ["git", "config", "user.name", "PACT CI"],
            ["git", "config", "user.email", "pact@example.invalid"],
            ["git", "add", "."],
            ["git", "commit", "-qm", "baseline"],
        ):
            subprocess.run(cmd, cwd=self.root, check=True, capture_output=True)
        self.task_id = "TASK-HANDOFF"
        prepared = self.pact(
            "task", "prepare", "Recover a test task",
            "--task-id", self.task_id,
            "--success", "Observable outcome stays correct",
            "--risk", "medium", "--no-code", "--json",
        )
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)

    def pact(self, *args):
        # Each call is a new Python process with no previous Chat context.
        return subprocess.run(
            [sys.executable, str(self.root / "pact.py"), *args],
            cwd=self.root, text=True, capture_output=True,
        )

    def test_checkpoint_resume_recover_without_inventing_completion(self):
        manifest_path = (
            self.root / ".pact" / "tasks" / self.task_id / "task.json"
        )
        before = json.loads(manifest_path.read_text())
        result = self.pact(
            "task", "checkpoint", self.task_id,
            "--done", "Looked up current implementation",
            "--todo", "Run acceptance checks",
            "--assumption", "Rejected plan premises still need review",
            "--json",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["checkpoint_count"], 1)
        handoff = self.root / ".pact" / "tasks" / self.task_id / "handoff.json"
        self.assertTrue(handoff.exists())

        recovered = self.pact("task", "resume", self.task_id, "--json")
        self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)
        data = json.loads(recovered.stdout)
        self.assertEqual(data["prepared_status"], "prepared")
        self.assertEqual(data["task_intent"], "Recover a test task")
        self.assertTrue(data["acceptance_criteria"])
        self.assertTrue(data["untrusted_agent_narrative"])
        self.assertTrue(data["reexamine_decision_premises"])
        self.assertFalse(data["owner_completed_automatically"])
        self.assertIn("Run acceptance checks", data["checkpoint_entries"][0]["todo"])
        after = json.loads(manifest_path.read_text())
        self.assertEqual(after["status"], "prepared")
        self.assertEqual(after["contract_sha256"], before["contract_sha256"])
        self.assertEqual(after["context_sha256"], before["context_sha256"])
        self.assertNotEqual(self.pact("task", "finish", self.task_id).returncode, 0)

    def test_run_receipt_is_revalidated_after_workspace_change(self):
        verified = self.pact(
            "task", "verify", self.task_id,
            "--criterion", "AC-1", "--claim", "A command exited successfully",
            "--json", "--", sys.executable, "-c", "print('ok')",
        )
        self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
        ref = json.loads(verified.stdout)["run_receipt"]
        checkpoint = self.pact(
            "task", "checkpoint", self.task_id,
            "--receipt", ref, "--claim-id", "EV-VERIFY-1",
            "--todo", "Recheck results before completion",
        )
        self.assertEqual(checkpoint.returncode, 0, checkpoint.stderr)
        healthy = self.pact("task", "resume", self.task_id, "--json")
        self.assertEqual(healthy.returncode, 0, healthy.stdout + healthy.stderr)
        record = json.loads(healthy.stdout)
        self.assertEqual(record["handoff_references"][0]["state"], "same-file")
        self.assertFalse(record["evidence_errors"])

        (self.root / "README.md").write_text("changed after the check\n")
        stale = self.pact("task", "resume", self.task_id, "--json")
        self.assertEqual(stale.returncode, 1, stale.stdout + stale.stderr)
        report = json.loads(stale.stdout)
        self.assertTrue(report["evidence_errors"])
        self.assertEqual(report["handoff_references"][0]["state"], "stale-reverify")
        self.assertEqual(report["prepared_status"], "prepared")
        self.assertFalse(report["owner_completed_automatically"])

    def test_changed_decision_premise_requires_re_review_on_resume(self):
        decisions = self.root / ".agents" / "decisions"
        decisions.mkdir(parents=True, exist_ok=True)
        file = decisions / "cache-choice.md"
        file.write_text(
            "# Rejected alternative\nOriginal premise: no durable storage.\n",
            encoding="utf-8",
        )
        checkpoint = self.pact(
            "task", "checkpoint", self.task_id,
            "--decision", ".agents/decisions/cache-choice.md",
            "--todo", "Reconsider rejected cache alternative",
        )
        self.assertEqual(checkpoint.returncode, 0, checkpoint.stderr)
        healthy = self.pact("task", "resume", self.task_id, "--json")
        self.assertEqual(healthy.returncode, 0, healthy.stdout + healthy.stderr)
        first = json.loads(healthy.stdout)
        self.assertEqual(first["handoff_references"][0]["state"], "same-file")
        self.assertTrue(first["reexamine_decision_premises"])
        file.write_text(
            "# Rejected alternative\nNew premise: durable storage exists.\n",
            encoding="utf-8",
        )
        changed = self.pact("task", "resume", self.task_id, "--json")
        self.assertEqual(changed.returncode, 1, changed.stdout + changed.stderr)
        report = json.loads(changed.stdout)
        self.assertEqual(report["handoff_references"][0]["state"], "changed")
        self.assertTrue(any("premises" in x for x in report["warnings"]))
        self.assertEqual(report["prepared_status"], "prepared")
        self.assertFalse(report["owner_completed_automatically"])

    def test_invalid_handoff_is_controlled_error_and_task_state_unchanged(self):
        handoff = self.root / ".pact" / "tasks" / self.task_id / "handoff.json"
        handoff.write_text(json.dumps({
            "version": 1, "task_id": self.task_id,
            "entries": [{"command_to_run": "never execute"}],
        }), encoding="utf-8")
        rc = self.pact("task", "resume", self.task_id, "--json")
        self.assertEqual(rc.returncode, 2)
        self.assertIn("malformed", rc.stderr)
        self.assertEqual(self.pact("task", "status", self.task_id).returncode, 0)

    def test_unsafe_reference_rejected_before_checkpoint_write(self):
        fail = self.pact(
            "task", "checkpoint", self.task_id,
            "--decision", "../outside.md", "--done", "attempt",
        )
        self.assertEqual(fail.returncode, 2)
        self.assertFalse((
            self.root / ".pact" / "tasks" / self.task_id / "handoff.json"
        ).exists())

    def test_handoff_rejects_in_repo_symlink_alias_before_hashing(self):
        decisions = self.root / ".agents" / "decisions"
        decisions.mkdir(parents=True, exist_ok=True)
        actual = decisions / "genuine.md"
        actual.write_text("Durable rationale\n", encoding="utf-8")
        link = decisions / "alias.md"
        try:
            link.symlink_to(actual)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unsupported")
        result = self.pact(
            "task", "checkpoint", self.task_id,
            "--decision", ".agents/decisions/alias.md",
            "--todo", "Do not accept symlink alias",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("symlink", result.stderr.lower())
        self.assertFalse((
            self.root / ".pact" / "tasks" / self.task_id / "handoff.json"
        ).exists())

    def test_checkpoint_bounds_and_idempotent_history_append(self):
        too_long = self.pact(
            "task", "checkpoint", self.task_id,
            "--todo", "x" * 401,
        )
        self.assertEqual(too_long.returncode, 2)
        first = self.pact("task", "checkpoint", self.task_id, "--todo", "one")
        second = self.pact("task", "checkpoint", self.task_id, "--todo", "two")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        path = self.root / ".pact" / "tasks" / self.task_id / "handoff.json"
        data = json.loads(path.read_text())
        self.assertEqual(len(data["entries"]), 2)


if __name__ == "__main__":
    unittest.main()
