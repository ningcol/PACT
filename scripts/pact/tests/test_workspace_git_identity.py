"""Regression cases for PACT Git workspace identity and task attribution.

The fixtures use temporary repositories, never the developer's real Git state.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

RUNTIME = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNTIME))

import workspace


class GitWorkspaceIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-git-identity-")
        self.root = pathlib.Path(self.temp.name) / "project"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "pact@example.invalid")
        self.git("config", "user.name", "PACT Test")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git(self, *args: str, cwd: pathlib.Path | None = None) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd or self.root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(
            result.returncode, 0,
            f"git {args!r} failed: {result.stderr.decode(errors='replace')}",
        )
        return result.stdout.decode("utf-8", errors="surrogateescape").strip()

    def commit_all(self, name: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-qm", name)

    def gitlink(self) -> pathlib.Path:
        child = self.root / "sub"
        child.mkdir()
        self.git("init", "-q", cwd=child)
        self.git("config", "user.email", "pact@example.invalid", cwd=child)
        self.git("config", "user.name", "PACT Test", cwd=child)
        (child / "source.txt").write_text("version-A\n", encoding="utf-8")
        self.git("add", "source.txt", cwd=child)
        self.git("commit", "-qm", "child initial", cwd=child)
        sha = self.git("rev-parse", "HEAD", cwd=child)
        (self.root / "README.md").write_text("Parent\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("update-index", "--add", "--cacheinfo", f"160000,{sha},sub")
        self.git("commit", "-qm", "parent initial")
        return child

    def test_content_restored_to_original_head_does_not_count_as_task_change(self) -> None:
        file = self.root / "source.txt"
        file.write_text("original\n", encoding="utf-8")
        self.commit_all("initial")
        baseline = workspace.task_workspace_baseline(self.root)

        file.write_text("intermediate\n", encoding="utf-8")
        self.commit_all("intermediate commit")
        file.write_text("original\n", encoding="utf-8")
        delta = workspace.task_changed_files(self.root, baseline)
        self.assertEqual(delta["changed_files"], [])

    def test_git_autocrlf_normalized_restore_does_not_count_as_change(self) -> None:
        self.git("config", "core.autocrlf", "true")
        path = self.root / "line-endings.txt"
        path.write_bytes(b"original\r\n")
        self.commit_all("initial LF canonical blob")
        baseline = workspace.task_workspace_baseline(self.root)

        path.write_bytes(b"intermediate\r\n")
        self.commit_all("intermediate LF canonical blob")
        path.write_bytes(b"original\r\n")
        delta = workspace.task_changed_files(self.root, baseline)
        self.assertEqual(delta["changed_files"], [])

    def test_committed_change_is_attributed_when_final_content_differs(self) -> None:
        file = self.root / "source.txt"
        file.write_text("original\n", encoding="utf-8")
        self.commit_all("initial")
        baseline = workspace.task_workspace_baseline(self.root)
        file.write_text("final\n", encoding="utf-8")
        self.commit_all("final")
        self.assertEqual(workspace.task_changed_files(self.root, baseline)["changed_files"], ["source.txt"])

    @unittest.skipIf(os.name == "nt", "Windows uses backslash as a path separator")
    def test_posix_literal_backslash_is_not_converted_into_a_path_separator(self) -> None:
        self.assertEqual(
            workspace._decode_nul_paths(b"a\\b.txt\x00a/b.txt\x00"),
            ["a\\b.txt", "a/b.txt"],
        )
        (self.root / "a\\b.txt").write_text("literal\n", encoding="utf-8")
        (self.root / "a").mkdir()
        (self.root / "a" / "b.txt").write_text("nested\n", encoding="utf-8")
        self.commit_all("both distinct paths")
        baseline = workspace.task_workspace_baseline(self.root)
        (self.root / "a\\b.txt").write_text("changed literal\n", encoding="utf-8")
        self.assertEqual(
            workspace.task_changed_files(self.root, baseline)["changed_files"],
            ["a\\b.txt"],
        )

    def test_clean_initialized_gitlink_has_a_trustworthy_snapshot(self) -> None:
        self.gitlink()
        first = workspace.workspace_snapshot(self.root)
        second = workspace.workspace_snapshot(self.root)
        self.assertEqual(first["sha256"], second["sha256"])

    def test_dirty_gitlink_cannot_reuse_an_old_workspace_fingerprint(self) -> None:
        child = self.gitlink()
        (child / "source.txt").write_text("version-B\n", encoding="utf-8")
        with self.assertRaises(workspace.WorkspaceError):
            workspace.workspace_snapshot(self.root)

    def test_uninitialized_gitlink_rejects_workspace_snapshot(self) -> None:
        child = self.gitlink()
        # Moving the initialized submodule is portable even when Windows Git
        # objects are read-only and cannot be removed with shutil.rmtree().
        child.rename(self.root.parent / "detached-sub")
        child.mkdir()
        with self.assertRaises(workspace.WorkspaceError):
            workspace.workspace_snapshot(self.root)

    def test_moved_gitlink_head_is_detected_before_staging(self) -> None:
        child = self.gitlink()
        (child / "source.txt").write_text("version-B\n", encoding="utf-8")
        self.git("add", "source.txt", cwd=child)
        self.git("commit", "-qm", "child new commit", cwd=child)
        with self.assertRaises(workspace.WorkspaceError):
            workspace.workspace_snapshot(self.root)

    def test_clean_staged_gitlink_pointer_change_is_attributed(self) -> None:
        child = self.gitlink()
        baseline = workspace.task_workspace_baseline(self.root)
        (child / "source.txt").write_text("version-B\n", encoding="utf-8")
        self.git("add", "source.txt", cwd=child)
        self.git("commit", "-qm", "child new commit", cwd=child)
        self.git("add", "sub")
        delta = workspace.task_changed_files(self.root, baseline)
        self.assertEqual(delta["changed_files"], ["sub"])

    def test_dirty_gitlink_prevents_successful_run_receipt(self) -> None:
        child = self.gitlink()
        (child / "source.txt").write_text("modified\n", encoding="utf-8")
        output = self.root / "receipt.json"
        result = subprocess.run(
            [
                sys.executable, str(RUNTIME / "run.py"),
                "--task-id", "TASK-SUBMODULE", "--output", str(output),
                "--cwd", str(self.root), "--quiet",
                "--", sys.executable, "-c", "print('should-not-run')",
            ],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("submodule", result.stderr.lower())
        self.assertFalse(output.exists())

    @unittest.skipIf(os.name == "nt", "Windows treats backslash as a separator")
    def test_literal_backslash_does_not_impersonate_generated_state(self) -> None:
        self.assertFalse(workspace._excluded(r".pact\tasks\other.txt", set()))

    @unittest.skipIf(os.name == "nt", "chmod +x is not portable on Windows")
    def test_untracked_file_execute_bit_alters_verification_fingerprint(self) -> None:
        (self.root / "README.md").write_text("tracked\n", encoding="utf-8")
        self.commit_all("baseline")
        path = self.root / "scratch.sh"
        path.write_text("#!/bin/sh\n", encoding="utf-8")
        before = workspace.workspace_snapshot(self.root)["sha256"]
        path.chmod(path.stat().st_mode | 0o111)
        after = workspace.workspace_snapshot(self.root)["sha256"]
        self.assertNotEqual(before, after)

    @unittest.skipIf(os.name == "nt", "symlink creation is not portable on Windows")
    def test_symlink_restored_to_prepared_target_is_unchanged(self) -> None:
        (self.root / "a.txt").write_text("a", encoding="utf-8")
        (self.root / "b.txt").write_text("b", encoding="utf-8")
        link = self.root / "link.txt"
        link.symlink_to("a.txt")
        self.commit_all("initial")
        baseline = workspace.task_workspace_baseline(self.root)
        link.unlink()
        link.symlink_to("b.txt")
        self.commit_all("intermediate target")
        link.unlink()
        link.symlink_to("a.txt")
        self.assertNotIn(
            "link.txt",
            workspace.task_changed_files(self.root, baseline)["changed_files"],
        )

    def test_old_dirty_baseline_mode_is_normalized_without_false_change(self) -> None:
        self.assertEqual(
            workspace._compatible_prepared_state("mode:100:sha256:abc"),
            "mode:111:sha256:abc",
        )
        self.assertEqual(
            workspace._compatible_prepared_state("sha256:abc"),
            "symlink:sha256:abc",
        )

    @unittest.skipIf(os.name == "nt", "chmod +x is not portable on Windows")
    def test_executable_bit_change_is_attributed(self) -> None:
        file = self.root / "run.sh"
        file.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        self.commit_all("initial")
        baseline = workspace.task_workspace_baseline(self.root)
        file.chmod(file.stat().st_mode | 0o111)
        self.assertEqual(
            workspace.task_changed_files(self.root, baseline)["changed_files"], ["run.sh"]
        )

    @unittest.skipIf(os.name == "nt", "symlink creation is not portable on Windows")
    def test_symlink_target_changed_is_attributed(self) -> None:
        (self.root / "a.txt").write_text("a", encoding="utf-8")
        (self.root / "b.txt").write_text("b", encoding="utf-8")
        link = self.root / "link.txt"
        link.symlink_to("a.txt")
        self.commit_all("initial")
        baseline = workspace.task_workspace_baseline(self.root)
        link.unlink()
        link.symlink_to("b.txt")
        self.assertEqual(
            workspace.task_changed_files(self.root, baseline)["changed_files"], ["link.txt"]
        )


if __name__ == "__main__":
    unittest.main()
