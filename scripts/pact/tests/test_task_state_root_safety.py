"""Stage 4 RED regressions for prepared task preflight and internal state roots.

These tests use fully installed runtimes in disposable Git repositories.
They must fail against the original task finish/state root implementation.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
INIT = PROJECT_ROOT / "scripts" / "pact" / "init.py"


class TaskStateRootSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-pr04-state-")
        self.root = pathlib.Path(self.temp.name) / "project"
        self.root.mkdir()
        (self.root / "README.md").write_text(
            "# Project\n\nThe sample behavior remains correct.\n", encoding="utf-8"
        )
        init = subprocess.run(
            [sys.executable, str(INIT), "--target", str(self.root), "--apply"],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "config", "user.name", "PACT Test"], cwd=self.root, check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "pact@example.invalid"],
            cwd=self.root, check=True,
        )
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "adopt PACT"], cwd=self.root, check=True
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def pact(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.root / "pact.py"), *args],
            cwd=self.root, capture_output=True, text=True, timeout=60,
        )

    def prepare(self, task_id: str) -> dict:
        result = self.pact(
            "task", "prepare", "Preserve service behavior",
            "--success", "Behavior remains correct",
            "--risk", "low", "--task-id", task_id, "--json",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def alias_state_root(self, subdir: str) -> pathlib.Path:
        state = self.root / ".pact" / subdir
        outside = pathlib.Path(self.temp.name) / ("external-" + subdir)
        if state.exists():
            state.rename(outside)
        else:
            outside.mkdir()
        try:
            os.symlink(outside, state, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"directory symlinks unavailable: {exc}")
        return outside

    def assert_finish_has_no_effect(self, task_id: str, prepared: dict, expected_text: str) -> None:
        task_dir = self.root / ".pact" / "tasks" / task_id
        manifest = task_dir / "task.json"
        before = manifest.read_bytes()
        # Ensure a non-empty changed-file path would generate Final Impact
        # without the preflight. This must not run on invalid inputs.
        (self.root / "README.md").write_text(
            "# Project\n\nChange since task preparation.\n",
            encoding="utf-8",
        )
        finished = self.pact("task", "finish", task_id, "--json")
        self.assertEqual(finished.returncode, 2, finished.stdout + finished.stderr)
        self.assertIn(expected_text, finished.stderr)
        self.assertEqual(before, manifest.read_bytes(), "invalid input modified manifest")
        self.assertFalse((task_dir / "final-impact.json").exists())
        self.assertFalse((task_dir / "completion-attempts.jsonl").exists())

    def test_finish_checks_context_traversal_before_impact_or_manifest_write(self) -> None:
        task_id = "TASK-PR04-CONTEXT-ESCAPE"
        prep = self.prepare(task_id)
        manifest_file = self.root / ".pact" / "tasks" / task_id / "task.json"
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        manifest["context"] = "../not-repository-owned.json"
        manifest_file.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
        self.assert_finish_has_no_effect(task_id, prep, "context")

    def test_finish_checks_missing_context_before_impact_or_manifest_write(self) -> None:
        task_id = "TASK-PR04-CONTEXT-MISSING"
        prep = self.prepare(task_id)
        (self.root / prep["context"]).unlink()
        self.assert_finish_has_no_effect(task_id, prep, "context")

    def test_finish_checks_modified_context_before_impact_or_manifest_write(self) -> None:
        task_id = "TASK-PR04-CONTEXT-DRIFT"
        prep = self.prepare(task_id)
        context_path = self.root / prep["context"]
        context = json.loads(context_path.read_text(encoding="utf-8"))
        context["known_unknowns"].append("Modified after preparation.")
        context_path.write_text(json.dumps(context) + "\n", encoding="utf-8")
        self.assert_finish_has_no_effect(task_id, prep, "context_sha256")

    def test_prepare_rejects_external_tasks_root_without_creating_outside_task(self) -> None:
        outside = self.alias_state_root("tasks")
        task_id = "TASK-PR04-TASK-ROOT"
        result = self.pact(
            "task", "prepare", "Scope task state",
            "--success", "State stays in project",
            "--risk", "low", "--task-id", task_id, "--json",
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("state", result.stderr.lower())
        self.assertFalse((outside / task_id).exists())

    def test_prepare_rejects_external_completions_root(self) -> None:
        outside = self.alias_state_root("completions")
        task_id = "TASK-PR04-COMP-ROOT"
        result = self.pact(
            "task", "prepare", "Scope completion state",
            "--success", "State stays in project",
            "--risk", "low", "--task-id", task_id, "--json",
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("state", result.stderr.lower())
        self.assertFalse((outside / task_id).exists())

    def test_prepare_rejects_temporary_state_root_that_is_a_file(self) -> None:
        state = self.root / ".pact" / "tmp"
        if state.exists():
            state.rename(self.root / "old-tmp")
        state.write_text("not a directory\n", encoding="utf-8")
        task_id = "TASK-PR04-NOT-A-DIR"
        result = self.pact(
            "task", "prepare", "Reject invalid state root",
            "--success", "State stays in project",
            "--risk", "low", "--task-id", task_id, "--json",
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("state root must be a directory", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse((self.root / ".pact" / "tasks" / task_id).exists())

    def test_prepare_rejects_external_temporary_state_root(self) -> None:
        outside = self.alias_state_root("tmp")
        task_id = "TASK-PR04-TMP-ROOT"
        result = self.pact(
            "task", "prepare", "Scope temporary state",
            "--success", "State stays in project",
            "--risk", "low", "--task-id", task_id, "--json",
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("state", result.stderr.lower())
        self.assertFalse((self.root / ".pact" / "tasks" / task_id).exists())
        self.assertEqual(list(outside.iterdir()), [])

    def test_existing_tasks_root_alias_blocks_finish_status_and_eval(self) -> None:
        task_id = "TASK-PR04-STATE-ESCAPE"
        self.prepare(task_id)
        outside = self.alias_state_root("tasks")
        task_dir = outside / task_id
        original = (task_dir / "task.json").read_bytes()
        for args in (
            ("task", "finish", task_id, "--json"),
            ("task", "status", task_id, "--json"),
            ("eval", "--task", task_id, "--json"),
            ("eval", "--all-tasks", "--json"),
        ):
            with self.subTest(args=args):
                result = self.pact(*args)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("state", result.stderr.lower())
        self.assertEqual(original, (task_dir / "task.json").read_bytes())
        self.assertFalse((task_dir / "completion-attempts.jsonl").exists())
        self.assertFalse((task_dir / "final-impact.json").exists())

    def test_existing_default_completion_root_alias_blocks_finish_and_status(self) -> None:
        task_id = "TASK-PR04-BUNDLE-ESCAPE"
        self.prepare(task_id)
        outside = self.alias_state_root("completions")
        task_dir = self.root / ".pact" / "tasks" / task_id
        original = (task_dir / "task.json").read_bytes()
        for args in (
            ("task", "finish", task_id, "--json"),
            ("task", "status", task_id, "--json"),
        ):
            with self.subTest(args=args):
                result = self.pact(*args)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("state", result.stderr.lower())
        self.assertEqual(original, (task_dir / "task.json").read_bytes())
        self.assertFalse((task_dir / "completion-attempts.jsonl").exists())
        self.assertFalse((outside / task_id).exists())


    def test_broken_task_child_symlink_rejected_before_resolution(self) -> None:
        tasks = self.root / ".pact" / "tasks"
        tasks.mkdir(parents=True, exist_ok=True)
        link = tasks / "TASK-LINK"
        target = pathlib.Path(self.temp.name) / "uncreated-target"
        try:
            os.symlink(target, link, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"directory symlinks unavailable: {exc}")
        self.assertTrue(link.is_symlink())
        self.assertFalse(link.exists())
        result = self.pact("task", "status", "TASK-LINK")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("symlink/alias", result.stderr)


if __name__ == "__main__":
    unittest.main()
