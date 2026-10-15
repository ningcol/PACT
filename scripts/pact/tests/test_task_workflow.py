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


    @staticmethod
    def lock_command(mode: str, bundle: pathlib.Path) -> list[str]:
        """Exercise the real bundle lock in a separate process."""
        script = (
            "import os, pathlib, sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "from task_workflow import _exclusive_bundle\n"
            "try:\n"
            "    with _exclusive_bundle(pathlib.Path(sys.argv[2])):\n"
            "        if sys.argv[3] == 'crash': os._exit(19)\n"
            "        if sys.argv[3] == 'hold':\n"
            "            print('acquired', flush=True)\n"
            "            sys.stdin.readline()\n"
            "except ValueError as error:\n"
            "    print(error, file=sys.stderr)\n"
            "    sys.exit(7)\n"
        )
        return [
            sys.executable, "-c", script,
            str(ROOT / "scripts" / "pact"), str(bundle), mode,
        ]

    def test_writer_crash_does_not_strand_bundle(self) -> None:
        crash = subprocess.run(
            self.lock_command("crash", self.bundle),
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(crash.returncode, 19, crash.stderr)
        lock = self.bundle / ".task-workflow.lock"
        self.assertTrue(lock.is_file())
        drafted = self.pact("task", "draft", self.task_id)
        self.assertEqual(drafted.returncode, 0, drafted.stdout + drafted.stderr)
        # Keep one stable lock pathname to prevent split-inode concurrency.
        self.assertTrue(lock.is_file())

    def test_concurrent_bundle_writers_remain_exclusive(self) -> None:
        command = self.lock_command("hold", self.bundle)
        with subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        ) as writer:
            try:
                self.assertEqual(writer.stdout.readline().strip(), "acquired")
                blocked = self.pact("task", "draft", self.task_id)
                self.assertEqual(blocked.returncode, 2, blocked.stderr)
                self.assertIn("another task Evidence writer", blocked.stderr)
                self.assertFalse((self.bundle / "evidence.json").exists())
            finally:
                writer.communicate(input="\n", timeout=30)
            self.assertEqual(writer.returncode, 0)
        self.assertEqual(self.pact("task", "draft", self.task_id).returncode, 0)

    def test_legacy_empty_lock_file_is_reusable(self) -> None:
        self.bundle.mkdir(parents=True, exist_ok=True)
        lock = self.bundle / ".task-workflow.lock"
        lock.write_bytes(b"")
        drafted = self.pact("task", "draft", self.task_id)
        self.assertEqual(drafted.returncode, 0, drafted.stderr)
        self.assertTrue(lock.is_file())

    def test_symlinked_bundle_lock_fails_closed(self) -> None:
        self.bundle.mkdir(parents=True, exist_ok=True)
        outside = pathlib.Path(self.temp.name) / "outside.lock"
        outside.write_text("do not change", encoding="utf-8")
        try:
            (self.bundle / ".task-workflow.lock").symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("file symlinks unavailable")
        drafted = self.pact("task", "draft", self.task_id)
        self.assertEqual(drafted.returncode, 2, drafted.stdout + drafted.stderr)
        self.assertEqual(outside.read_text(encoding="utf-8"), "do not change")


    def test_finish_refuses_concurrent_same_task_state_writer(self) -> None:
        task_dir = self.root / ".pact" / "tasks" / self.task_id
        command = self.lock_command("hold", task_dir)
        with subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        ) as holder:
            try:
                self.assertEqual(holder.stdout.readline().strip(), "acquired")
                blocked = self.pact("task", "finish", self.task_id)
                self.assertEqual(blocked.returncode, 2, blocked.stderr)
                self.assertIn("another task Evidence writer", blocked.stderr)
                self.assertFalse(
                    (task_dir / "completion-attempts.jsonl").exists()
                )
            finally:
                holder.communicate(input="\n", timeout=30)
            self.assertEqual(holder.returncode, 0)
        resumed = self.pact("task", "finish", self.task_id)
        self.assertNotIn("another task Evidence writer", resumed.stderr)

    def test_verify_timeout_releases_lock_without_passing_evidence(self) -> None:
        result = self.pact(
            "task", "verify", self.task_id,
            "--criterion", "AC-1", "--claim", "Long running check",
            "--timeout-seconds", "1", "--",
            sys.executable, "-c", "import time; time.sleep(20)",
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("verification exceeded 1s", result.stderr)
        self.assertFalse((self.bundle / "evidence.json").exists())
        followup = self.verify()
        self.assertEqual(followup.returncode, 0, followup.stderr)

    def test_verify_rejects_nonpositive_timeout(self) -> None:
        result = self.pact(
            "task", "verify", self.task_id,
            "--criterion", "AC-1", "--claim", "Invalid timeout",
            "--timeout-seconds", "0", "--",
            sys.executable, "-c", "print('should not run')",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--timeout-seconds must be positive", result.stderr)


if __name__ == "__main__":
    unittest.main()
