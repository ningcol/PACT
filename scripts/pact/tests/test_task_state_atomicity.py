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
