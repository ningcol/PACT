from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
RUNTIME = PROJECT_ROOT / "scripts" / "pact"
sys.path.insert(0, str(RUNTIME))

import protocol_ids
import task as pact_task


class TaskStateAtomicityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-task-state-")
        self.root = pathlib.Path(self.temp.name)
        self.tasks = self.root / "tasks"
        self.tasks.mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_confined_child_rejects_internal_symlink_alias(self) -> None:
        real = self.tasks / "TASK-REAL"
        real.mkdir()
        alias = self.tasks / "TASK-ALIAS"
        try:
            os.symlink(real, alias, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")

        with self.assertRaisesRegex(ValueError, "real direct child"):
            protocol_ids.confined_child(self.tasks, "TASK-ALIAS")

        self.assertTrue(real.is_dir())
        self.assertTrue(alias.is_symlink())

    def test_confined_child_rejects_broken_symlink_alias(self) -> None:
        alias = self.tasks / "TASK-BROKEN"
        missing = self.tasks / "TASK-MISSING"
        try:
            os.symlink(missing, alias, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")

        with self.assertRaisesRegex(ValueError, "real direct child"):
            protocol_ids.confined_child(self.tasks, "TASK-BROKEN")

    def test_atomic_task_json_preserves_existing_file_when_commit_fails(self) -> None:
        task_dir = self.tasks / "TASK-ATOMIC"
        task_dir.mkdir()
        manifest = task_dir / "task.json"
        manifest.write_text('{"status":"prepared"}\n', encoding="utf-8")

        with mock.patch.object(
            pact_task.os,
            "replace",
            side_effect=OSError("simulated task manifest commit failure"),
        ):
            with self.assertRaisesRegex(OSError, "simulated task manifest commit failure"):
                pact_task.write_json(manifest, {"status": "completed"})

        self.assertEqual(
            json.loads(manifest.read_text(encoding="utf-8"))["status"],
            "prepared",
        )
        self.assertEqual(
            list(task_dir.glob(".task.json.pact-task-*.tmp")),
            [],
        )

    def test_atomic_completion_history_preserves_existing_file_when_commit_fails(self) -> None:
        task_dir = self.tasks / "TASK-HISTORY"
        task_dir.mkdir()
        history = task_dir / "completion-attempts.jsonl"
        original = {"version": 1, "complete": False}
        history.write_text(json.dumps(original) + "\n", encoding="utf-8")

        with mock.patch.object(
            pact_task.os,
            "replace",
            side_effect=OSError("simulated history commit failure"),
        ):
            with self.assertRaisesRegex(OSError, "simulated history commit failure"):
                pact_task.append_jsonl_atomic(
                    history,
                    {"version": 1, "complete": True},
                )

        self.assertEqual(
            history.read_text(encoding="utf-8"),
            json.dumps(original) + "\n",
        )
        self.assertEqual(
            list(task_dir.glob(".completion-attempts.jsonl.pact-task-*.tmp")),
            [],
        )

    def test_atomic_completion_history_rejects_corrupt_existing_jsonl(self) -> None:
        task_dir = self.tasks / "TASK-HISTORY-CORRUPT"
        task_dir.mkdir()
        history = task_dir / "completion-attempts.jsonl"
        history.write_text('{"version":1}\n{"broken"\n', encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "invalid JSONL history"):
            pact_task.append_jsonl_atomic(
                history,
                {"version": 1, "complete": True},
            )

        self.assertEqual(
            history.read_text(encoding="utf-8"),
            '{"version":1}\n{"broken"\n',
        )

    def test_final_impact_publish_replaces_leaf_symlink_without_following_target(self) -> None:
        task_dir = self.tasks / "TASK-IMPACT"
        task_dir.mkdir()
        outside = self.root / "outside-impact.json"
        outside.write_text('{"outside":true}\n', encoding="utf-8")
        destination = task_dir / "final-impact.json"
        try:
            os.symlink(outside, destination)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")

        def fake_run(command):
            output = pathlib.Path(command[command.index("--output") + 1])
            self.assertNotEqual(output, destination)
            self.assertEqual(output.parent, destination.parent)
            output.write_text('{"changed_files":["src/a.py"]}\n', encoding="utf-8")
            return pact_task.subprocess.CompletedProcess(command, 0, "", "")

        with mock.patch.object(pact_task, "run", side_effect=fake_run):
            result = pact_task.run_impact_atomically(
                ["impact", "--output", str(destination), "--files", "src/a.py"],
                destination,
            )

        self.assertEqual(result.returncode, 0)
        self.assertFalse(destination.is_symlink())
        self.assertEqual(
            json.loads(destination.read_text(encoding="utf-8"))["changed_files"],
            ["src/a.py"],
        )
        self.assertEqual(
            json.loads(outside.read_text(encoding="utf-8")),
            {"outside": True},
        )
        self.assertEqual(
            list(task_dir.glob(".final-impact.json.pact-task-*.tmp")),
            [],
        )

    def test_final_impact_commit_failure_preserves_existing_canonical_file(self) -> None:
        task_dir = self.tasks / "TASK-IMPACT-COMMIT-FAIL"
        task_dir.mkdir()
        destination = task_dir / "final-impact.json"
        destination.write_text('{"old":true}\n', encoding="utf-8")

        def fake_run(command):
            output = pathlib.Path(command[command.index("--output") + 1])
            output.write_text('{"changed_files":["src/a.py"]}\n', encoding="utf-8")
            return pact_task.subprocess.CompletedProcess(command, 0, "", "")

        with mock.patch.object(pact_task, "run", side_effect=fake_run):
            with mock.patch.object(
                pact_task.os,
                "replace",
                side_effect=OSError("simulated final impact commit failure"),
            ):
                with self.assertRaisesRegex(
                    OSError,
                    "simulated final impact commit failure",
                ):
                    pact_task.run_impact_atomically(
                        ["impact", "--output", str(destination), "--files", "src/a.py"],
                        destination,
                    )

        self.assertEqual(
            json.loads(destination.read_text(encoding="utf-8")),
            {"old": True},
        )
        self.assertEqual(
            list(task_dir.glob(".final-impact.json.pact-task-*.tmp")),
            [],
        )

    def test_final_impact_failure_preserves_existing_canonical_file(self) -> None:
        task_dir = self.tasks / "TASK-IMPACT-FAIL"
        task_dir.mkdir()
        destination = task_dir / "final-impact.json"
        destination.write_text('{"old":true}\n', encoding="utf-8")

        def fake_run(command):
            output = pathlib.Path(command[command.index("--output") + 1])
            output.write_text('{"partial":true}\n', encoding="utf-8")
            return pact_task.subprocess.CompletedProcess(command, 1, "", "failed")

        with mock.patch.object(pact_task, "run", side_effect=fake_run):
            result = pact_task.run_impact_atomically(
                ["impact", "--output", str(destination), "--files", "src/a.py"],
                destination,
            )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            json.loads(destination.read_text(encoding="utf-8")),
            {"old": True},
        )
        self.assertEqual(
            list(task_dir.glob(".final-impact.json.pact-task-*.tmp")),
            [],
        )

    def test_completion_bundle_path_preserves_absolute_custom_path(self) -> None:
        absolute = self.root / "external-completion" / "TASK-ABS"
        resolved = pact_task.completion_bundle_path(
            {"completion_bundle": str(absolute)},
            "TASK-ABS",
        )
        self.assertEqual(resolved, absolute)

    def test_task_manifest_reader_rejects_leaf_symlink(self) -> None:
        task_dir = self.tasks / "TASK-LINK"
        task_dir.mkdir()
        outside = self.root / "outside-task.json"
        outside.write_text('{"status":"prepared"}\n', encoding="utf-8")
        manifest = task_dir / "task.json"
        try:
            os.symlink(outside, manifest)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")

        with self.assertRaisesRegex(ValueError, "must not be a symlink"):
            pact_task.read_task_manifest(manifest)

        self.assertEqual(
            json.loads(outside.read_text(encoding="utf-8"))["status"],
            "prepared",
        )


if __name__ == "__main__":
    unittest.main()
