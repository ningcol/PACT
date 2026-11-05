"""Force reprepare preserves prior state without lending it current authority."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SOURCE = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SOURCE / "scripts/pact"))
import task
import task_workflow  # Bind source-module roots before task-local mocks below.
from task_history import prior_generations


class TaskHistoryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="pact-history-")
        self.addCleanup(temp.cleanup)
        self.root = pathlib.Path(temp.name).resolve()
        self.tasks = self.root / ".pact/tasks"
        self.completions = self.root / ".pact/completions"
        self.tmp = self.root / ".pact/tmp"
        self.task_dir = self.tasks / "TASK-HISTORY"
        self.bundle = self.completions / "TASK-HISTORY"
        self.task_dir.mkdir(parents=True)
        self.bundle.mkdir(parents=True)
        self.old = {
            "task_id": "TASK-HISTORY", "status": "completed",
            "created_at": "2026-01-01T00:00:00Z",
            "completed_at": "2026-01-02T00:00:00Z",
            "workspace_baseline": {"git_head": "original-head"},
        }
        (self.task_dir / "task.json").write_text(json.dumps(self.old))
        (self.task_dir / "contract.json").write_bytes(b"old contract bytes\n")
        (self.bundle / "evidence.json").write_bytes(b"old evidence bytes\n")
        runs = self.root / ".pact/runs/TASK-HISTORY"
        runs.mkdir(parents=True)
        (runs / "old.json").write_bytes(b"unchanged run\n")
        self.args = argparse.Namespace(
            task_id="TASK-HISTORY", task="Updated intent", success="New outcome",
            acceptance=[], constraint=[], force=True, goal=None, risk="low",
            intent=None, scope_first=False, nonfunctional=False,
            full_decisions=False, required_rules=[], query=[], token_budget=None,
            limit=None, code=False, files=[], base=None, head="HEAD", json=True,
        )

    def prepare(self, failure=None):
        def run(command):
            if "context" in command:
                output = pathlib.Path(command[command.index("--output") + 1])
                output.write_text('{"artifacts": []}')
            return subprocess.CompletedProcess(command, 0, "", "")

        patches = (
            mock.patch.object(task, "ROOT", self.root),
            mock.patch.object(task, "TASK_ROOT", self.tasks),
            mock.patch.object(task, "COMPLETION_ROOT", self.completions),
            mock.patch.object(task, "TMP_ROOT", self.tmp),
            mock.patch.object(task, "task_workspace_baseline", return_value={"kind": "git", "git_head": "new-head", "dirty_files": {}}),
            mock.patch.object(task, "run", side_effect=run),
        )
        with contextlib.ExitStack() as stack:
            for patch in patches:
                stack.enter_context(patch)
            if failure is not None:
                stack.enter_context(mock.patch.object(task.os, "replace", side_effect=failure))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            errors = io.StringIO()
            stack.enter_context(contextlib.redirect_stderr(errors))
            result = task.prepare(self.args)
            self.last_error = errors.getvalue()
            return result

    def test_force_preserves_completed_bytes_and_prior_baseline(self):
        self.assertEqual(self.prepare(), 0, self.last_error)
        result = prior_generations(self.root, "TASK-HISTORY")
        self.assertFalse(result["truncated"])
        self.assertEqual(len(result["items"]), 1)
        item = result["items"][0]
        self.assertEqual(item["status"], "completed")
        self.assertEqual(item["base_git_head"], "original-head")
        archived = self.root / item["path"]
        self.assertEqual(json.loads((archived / "task/task.json").read_text()), self.old)
        self.assertEqual((archived / "task/contract.json").read_bytes(), b"old contract bytes\n")
        self.assertEqual((archived / "completion/evidence.json").read_bytes(), b"old evidence bytes\n")
        current = json.loads((self.task_dir / "task.json").read_text())
        self.assertEqual(current["status"], "prepared")
        self.assertEqual(current["workspace_baseline"]["git_head"], "new-head")
        self.assertFalse(self.bundle.exists())
        self.assertFalse((archived / "runs").exists())
        self.assertEqual((self.root / ".pact/runs/TASK-HISTORY/old.json").read_bytes(), b"unchanged run\n")

    def test_repeated_force_does_not_nest_history(self):
        self.assertEqual(self.prepare(), 0)
        self.assertEqual(self.prepare(), 0)
        items = prior_generations(self.root, "TASK-HISTORY")["items"]
        self.assertEqual(len(items), 2)
        self.assertEqual({i["status"] for i in items}, {"prepared", "completed"})
        self.assertFalse(any(p.name == ".history" for i in items for p in (self.root / i["path"]).rglob("*")))

    def test_publish_failure_restores_old_state_and_removes_archive(self):
        original = task.os.replace

        def replace(source, destination):
            if pathlib.Path(source).name == "task" and pathlib.Path(destination) == self.task_dir:
                raise OSError("injected task publish failure")
            return original(source, destination)

        self.assertEqual(self.prepare(replace), 2)
        self.assertEqual(json.loads((self.task_dir / "task.json").read_text()), self.old)
        self.assertEqual((self.bundle / "evidence.json").read_bytes(), b"old evidence bytes\n")
        self.assertEqual(prior_generations(self.root, "TASK-HISTORY")["items"], [])

    def test_history_publish_failure_restores_old_state(self):
        original = task.os.replace

        def replace(source, destination):
            if pathlib.Path(source).name == "history":
                raise OSError("injected history publish failure")
            return original(source, destination)

        self.assertEqual(self.prepare(replace), 2)
        self.assertEqual(json.loads((self.task_dir / "task.json").read_text()), self.old)
        self.assertTrue((self.bundle / "evidence.json").is_file())

    def test_unsafe_history_ancestor_fails_without_replacing_old_task(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.tasks / ".history").symlink_to(outside, target_is_directory=True)
        self.assertEqual(self.prepare(), 2)
        self.assertEqual(json.loads((self.task_dir / "task.json").read_text()), self.old)
        self.assertTrue((self.bundle / "evidence.json").is_file())
        self.assertEqual(list(outside.iterdir()), [])
        with self.assertRaisesRegex(ValueError, "symlink"):
            prior_generations(self.root, "TASK-HISTORY")

    def test_corrupt_history_is_explicit_and_old_tasks_need_no_history(self):
        self.assertEqual(prior_generations(self.root, "TASK-HISTORY")["items"], [])
        self.assertEqual(self.prepare(), 0)
        item = prior_generations(self.root, "TASK-HISTORY")["items"][0]
        (self.root / item["path"] / "task/task.json").write_text("broken")
        with self.assertRaisesRegex(ValueError, "historical task manifest"):
            prior_generations(self.root, "TASK-HISTORY")

    def test_custom_local_bundle_is_snapshotted_without_moving_original(self):
        custom = self.root / "delivery/custom"
        custom.mkdir(parents=True)
        (custom / "evidence.json").write_bytes(b"custom evidence")
        self.old["completion_bundle"] = "delivery/custom"
        (self.task_dir / "task.json").write_text(json.dumps(self.old))
        self.assertEqual(self.prepare(), 0)
        item = prior_generations(self.root, "TASK-HISTORY")["items"][0]
        self.assertTrue(item["completion_snapshot"])
        self.assertFalse(item["external_completion_preserved"])
        self.assertEqual(item["completion_reference"], "delivery/custom")
        self.assertEqual((custom / "evidence.json").read_bytes(), b"custom evidence")
        archived = self.root / item["path"]
        self.assertEqual((archived / "completion/evidence.json").read_bytes(), b"custom evidence")
        self.assertEqual((archived / "default-completion/evidence.json").read_bytes(), b"old evidence bytes\n")

    def test_external_bundle_is_preserved_only_as_reference(self):
        external = self.root.parent / (self.root.name + "-external")
        external.mkdir()
        self.addCleanup(lambda: __import__("shutil").rmtree(external))
        (external / "evidence.json").write_bytes(b"external evidence")
        self.old["completion_bundle"] = str(external)
        (self.task_dir / "task.json").write_text(json.dumps(self.old))
        self.assertEqual(self.prepare(), 0)
        item = prior_generations(self.root, "TASK-HISTORY")["items"][0]
        self.assertFalse(item["completion_snapshot"])
        self.assertTrue(item["external_completion_preserved"])
        self.assertFalse((self.root / item["path"] / "completion").exists())
        self.assertEqual((external / "evidence.json").read_bytes(), b"external evidence")

    def test_custom_bundle_symlink_ancestor_is_rejected(self):
        custom = self.root / "custom"
        custom.mkdir()
        (self.root / "custom-alias").symlink_to(custom, target_is_directory=True)
        self.old["completion_bundle"] = "custom-alias/result"
        (self.task_dir / "task.json").write_text(json.dumps(self.old))
        self.assertEqual(self.prepare(), 2)
        self.assertIn("symlink", self.last_error)
        self.assertEqual(json.loads((self.task_dir / "task.json").read_text()), self.old)

    def test_force_rejects_wrong_prior_identity_without_publishing(self):
        self.old["task_id"] = "OTHER-TASK"
        (self.task_dir / "task.json").write_text(json.dumps(self.old))
        self.assertEqual(self.prepare(), 2)
        self.assertIn("historical task identity", self.last_error)
        self.assertEqual(json.loads((self.task_dir / "task.json").read_text()), self.old)
        self.assertTrue((self.bundle / "evidence.json").is_file())
        self.assertEqual(prior_generations(self.root, "TASK-HISTORY")["items"], [])

    def test_force_rejects_wrong_prior_status_without_publishing(self):
        self.old["status"] = "invalid"
        (self.task_dir / "task.json").write_text(json.dumps(self.old))
        self.assertEqual(self.prepare(), 2)
        self.assertIn("historical task status", self.last_error)
        self.assertEqual(json.loads((self.task_dir / "task.json").read_text()), self.old)
        self.assertTrue((self.bundle / "evidence.json").is_file())
        self.assertEqual(prior_generations(self.root, "TASK-HISTORY")["items"], [])

    def test_bounded_summary_does_not_discard_older_generations(self):
        self.assertEqual(self.prepare(), 0)
        parent = self.tasks / ".history/TASK-HISTORY"
        import shutil
        source = next(parent.iterdir())
        for index in range(22):
            shutil.copytree(source, parent / f"20260101T000000{index:06d}Z-0123456789ab")
        result = prior_generations(self.root, "TASK-HISTORY")
        self.assertEqual(len(result["items"]), 20)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(list(parent.iterdir())), 23)


class InstalledTaskHistoryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="pact-history-cli-")
        self.addCleanup(temp.cleanup)
        self.root = pathlib.Path(temp.name).resolve()
        (self.root / "README.md").write_text("# Example\n")
        proc = subprocess.run(
            [sys.executable, str(SOURCE / "scripts/pact/init.py"), "--target", str(self.root), "--apply"],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for command in (
            ["git", "init", "-q"],
            ["git", "config", "user.name", "PACT Test"],
            ["git", "config", "user.email", "pact@example.invalid"],
            ["git", "add", "."],
            ["git", "commit", "-qm", "baseline"],
        ):
            subprocess.run(command, cwd=self.root, capture_output=True, check=True)
        self.prepare_args = (
            "task", "prepare", "Preserve a real task", "--task-id", "TASK-HISTORY",
            "--success", "the observable check passes", "--risk", "low", "--no-code", "--json",
        )
        proc = self.pact(*self.prepare_args)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def pact(self, *args):
        return subprocess.run(
            [sys.executable, str(self.root / "pact.py"), *args],
            cwd=self.root, capture_output=True, text=True,
        )

    def test_installed_status_resume_and_no_old_evidence_reuse(self):
        drafted = self.pact("task", "draft", "TASK-HISTORY")
        self.assertEqual(drafted.returncode, 0, drafted.stderr)
        checked = self.pact(
            "task", "verify", "TASK-HISTORY", "--criterion", "AC-1", "--claim", "A concrete check ran",
            "--", sys.executable, "-c", "print('a concrete successful check')",
        )
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        forced = self.pact(*self.prepare_args, "--force")
        self.assertEqual(forced.returncode, 0, forced.stdout + forced.stderr)
        for command in ("status", "resume"):
            result = self.pact("task", command, "TASK-HISTORY", "--json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            history = json.loads(result.stdout)["prior_generations"]
            self.assertEqual(len(history["items"]), 1)
            self.assertTrue(history["items"][0]["completion_present"])
        failed = self.pact("task", "finish", "TASK-HISTORY", "--json")
        self.assertNotEqual(failed.returncode, 0)
        current = json.loads((self.root / ".pact/tasks/TASK-HISTORY/task.json").read_text())
        self.assertEqual(current["status"], "prepared")

    def test_concurrent_force_writers_preserve_every_replaced_generation(self):
        procs = [subprocess.Popen(
            [sys.executable, str(self.root / "pact.py"), *self.prepare_args, "--force"],
            cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        ) for _ in range(2)]
        results = [(p, *p.communicate(timeout=60)) for p in procs]
        successes = sum(p.returncode == 0 for p, _, _ in results)
        self.assertGreaterEqual(successes, 1, results)
        for proc, stdout, stderr in results:
            self.assertIn(proc.returncode, (0, 2), stdout + stderr)
            if proc.returncode:
                self.assertIn("lock", stderr.lower())
        result = self.pact("task", "status", "TASK-HISTORY", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(len(data["prior_generations"]["items"]), successes)
        self.assertEqual(data["status"], "prepared")


if __name__ == "__main__":
    unittest.main()
