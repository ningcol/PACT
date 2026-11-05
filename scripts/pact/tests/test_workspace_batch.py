"""Batch Git reads retain the per-file identity contract without per-file processes."""

from __future__ import annotations

import hashlib
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import workspace


def legacy_delta(root, baseline):
    """The pre-batch attribution algorithm, using unchanged per-file primitives."""
    head = workspace._run_git(root, ["rev-parse", "HEAD"], text=True).stdout.strip()
    dirty = baseline["dirty_files"]
    paths = set(dirty) | workspace._git_changed_paths(root)
    paths.update(workspace._git_committed_candidate_paths(root, baseline["git_head"], head))
    filemode = workspace._git_filemode_enabled(root)
    changed = []
    for path in sorted(paths):
        prepared = dirty.get(path)
        if prepared is None:
            prepared = workspace._git_ref_file_state(root, baseline["git_head"], path)
        current = workspace._working_file_state(
            root, path, filemode_enabled=filemode, compare_committed=path not in dirty,
        )
        if current != workspace._compatible_prepared_state(prepared):
            changed.append(path)
    return changed


def legacy_snapshot(root):
    excluded = workspace.discovery_excluded_paths(root)
    head = workspace._run_git(root, ["rev-parse", "HEAD"], text=True).stdout.strip()
    staged = workspace._git_name_set(root, ["diff", "--cached", "--name-only", "--no-renames", "-z", "--"], excluded)
    unstaged = workspace._git_name_set(root, ["diff", "--name-only", "--no-renames", "-z", "--"], excluded)
    untracked = workspace._git_name_set(root, ["ls-files", "--others", "--exclude-standard", "-z"], excluded)
    digest = hashlib.sha256(b"PACT-WORKSPACE-V3\n" + f"HEAD:{head}\n".encode())
    filemode = workspace._git_filemode_enabled(root)
    for paths, label, get_state in (
        (staged, b"STAGED\0", lambda p: workspace._git_index_file_state(root, p)),
        (unstaged, b"UNSTAGED\0", lambda p: workspace._working_file_state(root, p, filemode_enabled=filemode)),
    ):
        for path in sorted(paths):
            digest.update(label + path.encode("utf-8", errors="surrogateescape") + b"\0")
            digest.update(get_state(path).encode() + b"\n")
    digest.update(b"UNTRACKED\n")
    for path in sorted(untracked):
        workspace._hash_untracked_file(digest, root, path)
    return digest.hexdigest()


class BatchWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pact-batch-workspace-")
        self.root = pathlib.Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "PACT")
        self.git("config", "user.email", "pact@example.invalid")

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True).stdout

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "fixture")

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def test_staged_unstaged_predirty_committed_and_restored_identity(self):
        for name in ["staged", "dirty", "deleted", "restored", "committed"]:
            self.write(name, b"base\n")
        self.commit()
        self.write("dirty", b"before task\r\n")
        self.write("pre-untracked", b"before task\n")
        baseline = workspace.task_workspace_baseline(self.root)
        self.write("committed", b"task commit\n")
        self.write("restored", b"intermediate\n")
        self.commit()
        self.write("restored", b"base\n")
        self.write("staged", b"index\n")
        self.git("add", "staged")
        self.write("staged", b"working\n")
        (self.root / "deleted").unlink()
        self.write("new", b"new\n")
        self.assertEqual(workspace.workspace_snapshot(self.root)["sha256"], legacy_snapshot(self.root))
        self.assertEqual(workspace.task_changed_files(self.root, baseline)["changed_files"], legacy_delta(self.root, baseline))
        self.assertEqual(workspace.task_changed_files(self.root, baseline)["changed_files"], ["committed", "deleted", "new", "staged"])
        self.write("dirty", b"changed after first call\n")
        self.assertIn("dirty", workspace.task_changed_files(self.root, baseline)["changed_files"])

    @unittest.skipIf(os.name == "nt", "POSIX-specific filename and executable semantics")
    def test_special_paths_filters_modes_and_binary_contents_match_legacy(self):
        names = ["space name", "tab\tname", "line\nname", 'quote"name', "back\\name", "-leading", "中文", "wild[*]?"]
        self.write(".gitattributes", b"* text eol=lf\n")
        for name in names:
            self.write(name, b"base\r\n")
        self.commit()
        baseline = workspace.task_workspace_baseline(self.root)
        for name in names:
            self.write(name, b"updated\r\n")
        (self.root / names[0]).chmod(0o755)
        self.assertEqual(workspace.task_changed_files(self.root, baseline)["changed_files"], legacy_delta(self.root, baseline))
        self.assertEqual(workspace.workspace_snapshot(self.root)["sha256"], legacy_snapshot(self.root))
        self.git("config", "core.filemode", "false")
        self.assertEqual(workspace.task_changed_files(self.root, baseline)["changed_files"], legacy_delta(self.root, baseline))

    @unittest.skipIf(os.name == "nt", "Windows filename encoding differs")
    def test_non_utf8_filename_when_supported_by_filesystem(self):
        name = "nonutf-\udcff"
        try:
            self.write(name, b"base\x00binary\n")
        except (OSError, UnicodeError) as exc:
            self.skipTest(f"filesystem cannot create non-UTF-8 filename: {exc}")
        self.commit()
        baseline = workspace.task_workspace_baseline(self.root)
        self.write(name, b"updated\x00binary\n")
        self.assertEqual(workspace.task_changed_files(self.root, baseline)["changed_files"], [name])
        self.assertEqual(workspace.workspace_snapshot(self.root)["sha256"], legacy_snapshot(self.root))

    def test_clean_filters_normalize_committed_but_not_predirty_bytes(self):
        self.write(".gitattributes", b"*.txt text eol=lf\n")
        self.write("clean.txt", b"base\r\n")
        self.write("dirty.txt", b"base\r\n")
        self.commit()
        self.write("dirty.txt", b"dirty\r\n")
        baseline = workspace.task_workspace_baseline(self.root)
        self.write("clean.txt", b"intermediate\r\n")
        self.commit()
        self.write("clean.txt", b"base\r\n")
        self.write("dirty.txt", b"dirty\n")
        self.assertEqual(workspace.task_changed_files(self.root, baseline)["changed_files"], ["dirty.txt"])

    def test_custom_clean_filter_and_binary_match_legacy(self):
        self.write("clean.py", b"import sys\nsys.stdout.buffer.write(sys.stdin.buffer.read().replace(b'MASK', b''))\n")
        command = f'"{pathlib.Path(sys.executable).as_posix()}" "{(self.root / "clean.py").as_posix()}"'
        self.git("config", "filter.fixture.clean", command)
        self.git("config", "filter.fixture.required", "true")
        self.write(".gitattributes", b"*.txt filter=fixture\n*.bin -text\n")
        self.write("clean.txt", b"baseMASK\n")
        self.write("dirty.txt", b"baseMASK\n")
        self.write("data.bin", b"base\x00bytes\n")
        self.commit()
        self.write("dirty.txt", b"dirtyMASK\n")
        baseline = workspace.task_workspace_baseline(self.root)
        self.write("clean.txt", b"middleMASK\n")
        self.commit()
        self.write("clean.txt", b"baseMASK\n")
        self.write("dirty.txt", b"dirty\n")
        self.write("data.bin", b"updated\x00bytes\n")
        self.assertEqual(workspace.task_changed_files(self.root, baseline)["changed_files"], ["data.bin", "dirty.txt"])
        self.assertEqual(workspace.task_changed_files(self.root, baseline)["changed_files"], legacy_delta(self.root, baseline))
        self.assertEqual(workspace.workspace_snapshot(self.root)["sha256"], legacy_snapshot(self.root))

    @unittest.skipIf(os.name == "nt", "symlink support depends on Windows permissions")
    def test_symlink_targets_and_text_checkouts_match_legacy(self):
        self.write("source", b"base\n")
        (self.root / "link").symlink_to("source")
        (self.root / "other-link").symlink_to("line\nsource")
        self.commit()
        baseline = workspace.task_workspace_baseline(self.root)
        (self.root / "link").unlink()
        (self.root / "link").symlink_to("new-target")
        self.assertEqual(workspace.task_changed_files(self.root, baseline)["changed_files"], legacy_delta(self.root, baseline))
        self.git("config", "core.symlinks", "false")
        (self.root / "other-link").unlink()
        self.write("other-link", b"line\nsource")
        self.assertEqual(workspace.task_changed_files(self.root, baseline)["changed_files"], ["link"])

    def test_hundreds_of_paths_use_bounded_batch_queries(self):
        for i in range(200):
            self.write(f"source-{i}.txt", b"base\n")
        self.commit()
        baseline = workspace.task_workspace_baseline(self.root)
        for i in range(200):
            self.write(f"source-{i}.txt", b"updated\n")
        with mock.patch.object(workspace, "_run_git", wraps=workspace._run_git) as run:
            changed = workspace.task_changed_files(self.root, baseline)
        self.assertEqual(len(changed["changed_files"]), 200)
        self.assertLess(run.call_count, 25)
        commands = [call.args[1] for call in run.call_args_list]
        self.assertEqual(sum(cmd == ["hash-object", "--stdin-paths"] for cmd in commands), 1)

    def test_sha256_repository_preserves_object_identities(self):
        self.root = self.root / "sha256"
        self.root.mkdir()
        result = subprocess.run(["git", "init", "--object-format=sha256", "-q"], cwd=self.root, capture_output=True)
        if result.returncode:
            self.skipTest("Git has no SHA-256 repository support")
        self.git("config", "user.name", "PACT")
        self.git("config", "user.email", "pact@example.invalid")
        self.write("source", b"base\n")
        self.commit()
        baseline = workspace.task_workspace_baseline(self.root)
        self.write("source", b"updated\n")
        self.assertEqual(workspace.task_changed_files(self.root, baseline)["changed_files"], ["source"])
        self.assertEqual(workspace.workspace_snapshot(self.root)["sha256"], legacy_snapshot(self.root))

    def test_batch_hash_errors_and_wrong_output_count_fail_closed(self):
        self.write("source", b"base\n")
        self.commit()
        baseline = workspace.task_workspace_baseline(self.root)
        self.write("source", b"updated\n")
        original = workspace._run_git
        for code, output in [(1, b""), (0, b""), (0, b"bad\n"), (0, b"a" * 40 + b"\n" + b"b" * 40 + b"\n")]:
            def run(root, args, **kwargs):
                if args == ["hash-object", "--stdin-paths"]:
                    return subprocess.CompletedProcess(args, code, stdout=output, stderr=b"")
                return original(root, args, **kwargs)
            with self.subTest(code=code, output=output), mock.patch.object(workspace, "_run_git", side_effect=run):
                with self.assertRaises(workspace.WorkspaceError):
                    workspace.task_changed_files(self.root, baseline)

    def test_malformed_batch_index_and_tree_fail_closed(self):
        self.write("source", b"base\n")
        self.commit()
        baseline = workspace.task_workspace_baseline(self.root)
        self.write("source", b"updated\n")
        original = workspace._run_git
        for target in (["ls-files", "--stage", "-z"], ["ls-tree", "-r", "-t", "-z", baseline["git_head"]]):
            def run(root, args, **kwargs):
                if args == target:
                    return subprocess.CompletedProcess(args, 0, stdout=b"malformed\0", stderr=b"")
                return original(root, args, **kwargs)
            with self.subTest(target=target), mock.patch.object(workspace, "_run_git", side_effect=run):
                with self.assertRaises(workspace.WorkspaceError):
                    workspace.task_changed_files(self.root, baseline)


if __name__ == "__main__":
    unittest.main()
