from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
RUNTIME = PROJECT_ROOT / "scripts" / "pact"
RUN = RUNTIME / "run.py"
sys.path.insert(0, str(RUNTIME))

spec = importlib.util.spec_from_file_location(
    "pact_workspace_reliability",
    RUNTIME / "workspace.py",
)
workspace = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(workspace)

run_spec = importlib.util.spec_from_file_location(
    "pact_run_reliability",
    RUN,
)
run_module = importlib.util.module_from_spec(run_spec)
assert run_spec.loader is not None
run_spec.loader.exec_module(run_module)


class StreamingReliabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-streaming-")
        self.root = pathlib.Path(self.temp.name) / "project"
        self.root.mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "pact-test@example.invalid"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "PACT Test"],
            cwd=self.root,
            check=True,
        )
        (self.root / "README.md").write_text("# Demo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "baseline"],
            cwd=self.root,
            check=True,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_run_hashes_large_streams_without_persisting_output(self) -> None:
        receipt = self.root / ".pact" / "runs" / "TASK-STREAM" / "run.json"
        stdout_chunk = b"A" * (1024 * 1024)
        stderr_chunk = b"B" * (1024 * 1024)
        stdout_repeats = 8
        stderr_repeats = 5

        code = (
            "import sys;"
            f"o=b'A'*{len(stdout_chunk)};"
            f"e=b'B'*{len(stderr_chunk)};"
            f"[sys.stdout.buffer.write(o) for _ in range({stdout_repeats})];"
            f"[sys.stderr.buffer.write(e) for _ in range({stderr_repeats})]"
        )
        result = subprocess.run(
            [
                sys.executable,
                str(RUN),
                "--task-id",
                "TASK-STREAM",
                "--output",
                str(receipt),
                "--cwd",
                str(self.root),
                "--quiet",
                "--",
                sys.executable,
                "-c",
                code,
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertTrue(receipt.is_file())

        data = json.loads(receipt.read_text(encoding="utf-8"))
        expected_stdout = hashlib.sha256()
        expected_stderr = hashlib.sha256()
        for _ in range(stdout_repeats):
            expected_stdout.update(stdout_chunk)
        for _ in range(stderr_repeats):
            expected_stderr.update(stderr_chunk)

        self.assertEqual(data["stdout_sha256"], expected_stdout.hexdigest())
        self.assertEqual(data["stderr_sha256"], expected_stderr.hexdigest())
        self.assertNotIn("stdout", data)
        self.assertNotIn("stderr", data)

    def test_git_workspace_snapshot_tracks_large_binary_content_without_diff_payload(self) -> None:
        binary = self.root / "large.bin"
        binary.write_bytes(b"A" * (6 * 1024 * 1024))
        subprocess.run(["git", "add", "large.bin"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "large baseline"],
            cwd=self.root,
            check=True,
        )

        clean = workspace.workspace_snapshot(self.root)
        self.assertFalse(clean["dirty"])

        binary.write_bytes(b"B" * (6 * 1024 * 1024))
        first = workspace.workspace_snapshot(self.root)
        self.assertTrue(first["dirty"])

        binary.write_bytes(b"C" * (6 * 1024 * 1024))
        second = workspace.workspace_snapshot(self.root)
        self.assertTrue(second["dirty"])
        self.assertNotEqual(first["sha256"], second["sha256"])

    def test_filesystem_workspace_snapshot_tracks_directory_symlink_target(self) -> None:
        fs_root = pathlib.Path(self.temp.name) / "filesystem"
        outside = pathlib.Path(self.temp.name) / "outside"
        target_a = outside / "a"
        target_b = outside / "b"
        fs_root.mkdir()
        target_a.mkdir(parents=True)
        target_b.mkdir(parents=True)
        link = fs_root / "linked-dir"
        try:
            os.symlink(target_a, link, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")

        first = workspace.filesystem_workspace_snapshot(fs_root)
        self.assertEqual(first["file_count"], 1)

        link.unlink()
        os.symlink(target_b, link, target_is_directory=True)
        second = workspace.filesystem_workspace_snapshot(fs_root)

        self.assertEqual(second["file_count"], 1)
        self.assertNotEqual(first["sha256"], second["sha256"])

    def test_atomic_receipt_replaces_leaf_symlink_without_following_target(self) -> None:
        receipt = self.root / ".pact" / "runs" / "TASK-SYMLINK" / "run.json"
        receipt.parent.mkdir(parents=True)
        outside = pathlib.Path(self.temp.name) / "outside-receipt.json"
        outside.write_text("KEEP-OUTSIDE\n", encoding="utf-8")
        try:
            os.symlink(outside, receipt)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")

        result = subprocess.run(
            [
                sys.executable,
                str(RUN),
                "--task-id",
                "TASK-SYMLINK",
                "--output",
                str(receipt),
                "--cwd",
                str(self.root),
                "--quiet",
                "--",
                sys.executable,
                "-c",
                "print('ok')",
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(receipt.is_symlink())
        self.assertEqual(outside.read_text(encoding="utf-8"), "KEEP-OUTSIDE\n")
        self.assertEqual(json.loads(receipt.read_text(encoding="utf-8"))["status"], "pass")

    def test_atomic_receipt_preserves_existing_file_when_commit_fails(self) -> None:
        receipt = self.root / ".pact" / "runs" / "TASK-ATOMIC" / "run.json"
        receipt.parent.mkdir(parents=True)
        receipt.write_text("ORIGINAL\n", encoding="utf-8")
        candidate = {
            "version": 2,
            "task_id": "TASK-ATOMIC",
        }

        with mock.patch.object(
            run_module.os,
            "replace",
            side_effect=OSError("simulated atomic commit failure"),
        ):
            with self.assertRaisesRegex(OSError, "simulated atomic commit failure"):
                run_module.publish_receipt(receipt, candidate)

        self.assertEqual(receipt.read_text(encoding="utf-8"), "ORIGINAL\n")
        self.assertEqual(
            list(receipt.parent.glob(".run.json.pact-run-*.tmp")),
            [],
        )


if __name__ == "__main__":
    unittest.main()
