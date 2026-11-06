"""Task navigation must explain facts without scanning or weakening completion."""
from __future__ import annotations

import argparse
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import task
import workspace


class TaskGuidanceTests(unittest.TestCase):
    def setUp(self):
        stack = self.enterContext(ExitStack())
        self.root = pathlib.Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="pact-guidance-")))
        for name, value in (
            ("ROOT", self.root), ("TASK_ROOT", self.root / ".pact/tasks"),
            ("COMPLETION_ROOT", self.root / ".pact/completions"),
        ):
            stack.enter_context(patch.object(task, name, value))
        self.task_id = "TASK-GUIDANCE"
        self.task_dir = task.TASK_ROOT / self.task_id
        self.task_dir.mkdir(parents=True)
        contract = {"version": 1, "task_id": self.task_id, "intent": "Check navigation",
                    "acceptance_criteria": [{"id": "AC-1", "kind": "outcome", "text": "Done"}]}
        self.manifest = {"version": 1, "task_id": self.task_id, "status": "prepared",
                         "risk_level": "low", "workspace_baseline": {
                             "kind": "git", "git_head": "a" * 40,
                             "dirty_files": {"existing.py": "state"}},
                         "completion_bundle": f".pact/completions/{self.task_id}"}
        for name, data in (("contract", contract), ("context", {})):
            path = self.task_dir / f"{name}.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            self.manifest[name] = path.relative_to(self.root).as_posix()
            self.manifest[name + "_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        task.write_json(self.task_dir / "task.json", self.manifest)

    def args(self, **kwargs):
        return argparse.Namespace(task_id=self.task_id, json=True, bundle=None,
                                  require_ci_metadata=False, require_knowledge_retention=False, **kwargs)

    def test_status_uses_stored_baseline_without_git_or_delta_scan(self):
        output = io.StringIO()
        with patch.object(workspace, "_run_git", side_effect=AssertionError("extra Git scan")), \
                patch.object(task, "task_changed_files", side_effect=AssertionError("extra delta")), \
                redirect_stdout(output):
            self.assertEqual(task.task_status(self.args()), 0)
        result = json.loads(output.getvalue())
        self.assertIn("pre-existing dirty paths: 1", result["baseline_summary"])
        self.assertIn("does not identify the writer", result["baseline_summary"])
        self.assertIn("--force", result["baseline_summary"])
        self.assertEqual(result["workspace_baseline"], self.manifest["workspace_baseline"])

    def test_non_git_baseline_is_unknown_instead_of_clean(self):
        result = task.baseline_summary({"kind": "filesystem", "workspace_sha256": "x"})
        self.assertIn("unavailable", result)
        self.assertIn("not zero", result)

    def test_failed_finish_navigation_is_read_only_and_preserves_status_and_exit(self):
        completed = subprocess.CompletedProcess([], 1, json.dumps({
            "complete": False, "errors": ["owner verification claim must exactly match Evidence"],
        }), "")
        for bundle in (None, "custom-completion"):
            with self.subTest(bundle=bundle):
                args = self.args()
                args.bundle = bundle
                output = io.StringIO()
                with patch.object(task, "task_changed_files", return_value={"supported": True, "changed_files": []}), \
                        patch.object(task, "run", return_value=completed) as run, redirect_stdout(output):
                    self.assertEqual(task._finish_locked(args), 1)
                result = json.loads(output.getvalue())
                self.assertFalse(result["complete"])
                self.assertEqual(result["blockers"], ["acceptance-gap"])
                self.assertEqual(run.call_count, 1)  # no assist, business check or draft executed
                self.assertEqual(json.loads((self.task_dir / "task.json").read_text())["status"], "prepared")
                if bundle is None:
                    self.assertIn(f"task assist {self.task_id} --json", result["next"])
                    self.assertIn("optional", result["next"])
                else:
                    self.assertIn("scoped to the saved bundle", result["next"])
                    self.assertIn("custom-completion", result["next"])
                    self.assertNotIn("--write-draft", result["next"])

    def test_status_and_failed_finish_do_not_recommend_unsupported_assist(self):
        external = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory(prefix="pact-external-bundle-")))
        original = dict(self.manifest)
        alias = f".pact/completions/../completions/{self.task_id}"
        for status, bundle in (("completed", original["completion_bundle"]),
                               ("prepared", str(external)), ("prepared", alias)):
            with self.subTest(status=status, bundle=bundle):
                task.write_json(self.task_dir / "task.json", {**original, "status": status, "completion_bundle": bundle})
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(task.task_status(self.args()), 0)
                next_step = json.loads(output.getvalue())["next"]
                self.assertNotIn(f"task assist {self.task_id}", next_step)
                self.assertIn(f"task resume {self.task_id}", next_step)
                output = io.StringIO()
                completed = subprocess.CompletedProcess([], 1, '{"complete": false, "errors": []}', "")
                with patch.object(task, "task_changed_files", return_value={"supported": True, "changed_files": []}), \
                        patch.object(task, "run", return_value=completed), redirect_stdout(output):
                    self.assertEqual(task._finish_locked(self.args()), 1)
                next_step = json.loads(output.getvalue())["next"]
                self.assertNotIn(f"task assist {self.task_id}", next_step)
                self.assertNotIn("--write-draft", next_step)

    def test_same_bundle_override_alias_does_not_claim_a_different_bundle(self):
        (self.root / self.manifest["completion_bundle"]).mkdir(parents=True)
        args = self.args()
        args.bundle = f".pact/completions/../completions/{self.task_id}"
        output = io.StringIO()
        completed = subprocess.CompletedProcess([], 1, '{"complete": false, "errors": []}', "")
        with patch.object(task, "task_changed_files", return_value={"supported": True, "changed_files": []}), \
                patch.object(task, "run", return_value=completed), redirect_stdout(output):
            self.assertEqual(task._finish_locked(args), 1)
        self.assertIn(f"task assist {self.task_id} --json", json.loads(output.getvalue())["next"])
        self.assertEqual(json.loads((self.task_dir / "task.json").read_text())["completion_bundle"],
                         self.manifest["completion_bundle"])

    def test_missing_bundle_files_keep_exit_and_stdout_but_add_safe_navigation(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        # Use the real complete command: its early missing-file branch has no JSON.
        with patch.object(task, "task_changed_files", return_value={"supported": True, "changed_files": []}), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(task._finish_locked(self.args()), 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("missing bundle file(s)", stderr.getvalue())
        self.assertIn(f"task assist {self.task_id} --json", stderr.getvalue())
        self.assertIn("task draft", stderr.getvalue())
        self.assertFalse((self.root / self.manifest["completion_bundle"]).exists())

    def test_unknown_non_json_failure_does_not_suggest_recovery_blindly(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        completed = subprocess.CompletedProcess([], 2, "", "PACT complete: invalid input\n")
        with patch.object(task, "task_changed_files", return_value={"supported": True, "changed_files": []}), \
                patch.object(task, "run", return_value=completed), redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(task._finish_locked(self.args()), 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertNotIn("task assist", stderr.getvalue())

    def test_frozen_context_preflight_error_does_not_suggest_assist_or_force(self):
        (self.task_dir / "context.json").write_text('{"changed": true}', encoding="utf-8")
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(task, "run") as run, redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(task._finish_locked(self.args()), 2)
        run.assert_not_called()
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("context_sha256", stderr.getvalue())
        self.assertNotIn("assist", stderr.getvalue())
        self.assertNotIn("--force", stderr.getvalue())

    def test_custom_bundle_failure_with_invalid_saved_path_still_records_attempt(self):
        self.manifest["completion_bundle"] = 42
        task.write_json(self.task_dir / "task.json", self.manifest)
        args = self.args()
        args.bundle = "custom-completion"
        output = io.StringIO()
        completed = subprocess.CompletedProcess([], 1, '{"complete": false, "errors": []}', "")
        with patch.object(task, "task_changed_files", return_value={"supported": True, "changed_files": []}), \
                patch.object(task, "run", return_value=completed), redirect_stdout(output):
            self.assertEqual(task._finish_locked(args), 1)
        self.assertIn("saved bundle path is invalid", json.loads(output.getvalue())["next"])
        self.assertTrue((self.task_dir / "completion-attempts.jsonl").is_file())


if __name__ == "__main__":
    unittest.main()
