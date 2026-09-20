"""Exact working-tree state binding for PACT verification receipts."""

from __future__ import annotations

import hashlib
import os
import pathlib
import subprocess

from distribution import discovery_excluded_paths


CONTROL_PLANE_EXACT_PATHS = {
    ".pact/install.json",
}

GENERATED_PREFIXES = (
    ".pact/cache/",
    ".pact/runs/",
    ".pact/completions/",
    ".pact/tasks/",
    ".pact/tmp/",
)


class WorkspaceError(RuntimeError):
    pass


def _run_git(root: pathlib.Path, args: list[str], *, text: bool = False):
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=text,
        timeout=30,
        check=False,
    )


def git_root(cwd: pathlib.Path) -> pathlib.Path | None:
    try:
        result = _run_git(cwd, ["rev-parse", "--show-toplevel"], text=True)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return pathlib.Path(result.stdout.strip()).resolve()


def _excluded(relative: str, installed_exclusions: set[str]) -> bool:
    normalized = relative.replace("\\", "/")
    if normalized in CONTROL_PLANE_EXACT_PATHS:
        return True
    if normalized in installed_exclusions:
        return True
    return any(
        normalized == prefix.rstrip("/") or normalized.startswith(prefix)
        for prefix in GENERATED_PREFIXES
    )


def _hash_untracked_file(digest, root: pathlib.Path, relative: str) -> None:
    path = root / relative
    digest.update(b"untracked\0")
    digest.update(relative.encode("utf-8", errors="surrogateescape"))
    digest.update(b"\0")

    try:
        if path.is_symlink():
            digest.update(b"symlink\0")
            digest.update(os.readlink(path).encode("utf-8", errors="surrogateescape"))
            digest.update(b"\n")
            return

        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\n")
    except OSError as exc:
        raise WorkspaceError(f"cannot fingerprint untracked file {relative}: {exc}") from exc


def _git_index_file_state(root: pathlib.Path, relative: str) -> str:
    try:
        result = _run_git(
            root,
            ["ls-files", "--stage", "-z", "--", relative],
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkspaceError(
            f"cannot inspect staged file {relative}: {exc}"
        ) from exc
    if result.returncode != 0:
        raise WorkspaceError(f"cannot inspect staged file {relative}")
    if not result.stdout:
        return "missing"
    return "index-sha256:" + hashlib.sha256(result.stdout).hexdigest()


def _git_name_set(
    root: pathlib.Path,
    args: list[str],
    installed_exclusions: set[str],
) -> set[str]:
    try:
        result = _run_git(root, args)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkspaceError(
            "cannot enumerate Git workspace paths: " + str(exc)
        ) from exc
    if result.returncode != 0:
        raise WorkspaceError(
            "Git workspace path enumeration failed: " + " ".join(args)
        )
    return {
        path
        for path in _decode_nul_paths(result.stdout)
        if path and not _excluded(path, installed_exclusions)
    }


def git_workspace_snapshot(cwd: pathlib.Path) -> dict | None:
    root = git_root(cwd)
    if root is None:
        return None

    installed_exclusions = discovery_excluded_paths(root)

    try:
        head_result = _run_git(root, ["rev-parse", "HEAD"], text=True)
        head = head_result.stdout.strip() if head_result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkspaceError(f"cannot inspect Git workspace: {exc}") from exc

    staged_paths = _git_name_set(
        root,
        ["diff", "--cached", "--name-only", "--no-renames", "-z", "--"],
        installed_exclusions,
    )
    unstaged_paths = _git_name_set(
        root,
        ["diff", "--name-only", "--no-renames", "-z", "--"],
        installed_exclusions,
    )
    untracked_paths = _git_name_set(
        root,
        ["ls-files", "--others", "--exclude-standard", "-z"],
        installed_exclusions,
    )

    digest = hashlib.sha256()
    digest.update(b"PACT-WORKSPACE-V2\n")
    digest.update(f"HEAD:{head or '<none>'}\n".encode())

    for relative in sorted(staged_paths):
        digest.update(b"STAGED\0")
        digest.update(relative.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        digest.update(_git_index_file_state(root, relative).encode("ascii"))
        digest.update(b"\n")

    for relative in sorted(unstaged_paths):
        digest.update(b"UNSTAGED\0")
        digest.update(relative.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        digest.update(_working_file_state(root, relative).encode("ascii"))
        digest.update(b"\n")

    digest.update(b"UNTRACKED\n")
    for relative in sorted(untracked_paths):
        _hash_untracked_file(digest, root, relative)

    dirty = bool(staged_paths or unstaged_paths or untracked_paths)

    return {
        "kind": "git",
        "sha256": digest.hexdigest(),
        "git_head": head,
        "dirty": dirty,
        "untracked_count": len(untracked_paths),
    }


def _filesystem_paths(root: pathlib.Path) -> list[pathlib.Path]:
    excluded_dirs = {".git", "__pycache__"}
    installed_exclusions = discovery_excluded_paths(root)
    paths: list[pathlib.Path] = []

    for current, dirs, files in os.walk(root):
        current_path = pathlib.Path(current)
        relative_dir = current_path.relative_to(root).as_posix()

        retained_dirs: list[str] = []
        for name in dirs:
            path = current_path / name
            relative = (
                f"{relative_dir}/{name}" if relative_dir != "." else name
            )
            excluded = (
                name in excluded_dirs
                or _excluded(relative.rstrip("/") + "/", installed_exclusions)
            )
            if excluded:
                continue
            if path.is_symlink():
                # os.walk(followlinks=False) exposes directory symlinks in dirs
                # but does not traverse them. Hash the link itself so retargeting
                # invalidates filesystem-backed run receipts.
                paths.append(path)
                continue
            retained_dirs.append(name)
        dirs[:] = retained_dirs

        for name in files:
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if _excluded(relative, installed_exclusions):
                continue
            paths.append(path)

    return sorted(paths, key=lambda p: p.relative_to(root).as_posix())


def filesystem_workspace_snapshot(cwd: pathlib.Path) -> dict:
    root = cwd.resolve()
    digest = hashlib.sha256()
    digest.update(b"PACT-WORKSPACE-FS-V1\n")

    count = 0
    for path in _filesystem_paths(root):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        try:
            if path.is_symlink():
                digest.update(b"symlink\0")
                digest.update(os.readlink(path).encode("utf-8", errors="surrogateescape"))
            else:
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
        except OSError as exc:
            raise WorkspaceError(f"cannot fingerprint {relative}: {exc}") from exc
        digest.update(b"\n")
        count += 1

    return {
        "kind": "filesystem",
        "sha256": digest.hexdigest(),
        "git_head": None,
        "dirty": None,
        "untracked_count": None,
        "file_count": count,
    }


def workspace_snapshot(cwd: pathlib.Path) -> dict:
    git = git_workspace_snapshot(cwd)
    return git if git is not None else filesystem_workspace_snapshot(cwd)


def _decode_nul_paths(data: bytes) -> list[str]:
    return [
        item.decode("utf-8", errors="surrogateescape").replace("\\", "/")
        for item in data.split(b"\0")
        if item
    ]


def _working_file_state(root: pathlib.Path, relative: str) -> str:
    path = root / relative
    if path.is_symlink():
        payload = b"symlink\0" + os.readlink(path).encode(
            "utf-8",
            errors="surrogateescape",
        )
        return "sha256:" + hashlib.sha256(payload).hexdigest()
    if not path.is_file():
        return "missing"

    digest = hashlib.sha256()
    try:
        mode = path.stat().st_mode & 0o111
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise WorkspaceError(f"cannot hash workspace file {relative}: {exc}") from exc
    return f"mode:{mode:o}:sha256:" + digest.hexdigest()


def _git_ref_file_state(
    root: pathlib.Path,
    ref: str,
    relative: str,
) -> str:
    try:
        result = _run_git(root, ["show", f"{ref}:{relative}"])
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkspaceError(
            f"cannot inspect prepared Git file {relative}: {exc}"
        ) from exc
    if result.returncode != 0:
        return "missing"
    return "sha256:" + hashlib.sha256(result.stdout).hexdigest()


def _git_changed_paths(root: pathlib.Path) -> set[str]:
    installed_exclusions = discovery_excluded_paths(root)
    commands = [
        ["diff", "--cached", "--name-only", "--no-renames", "-z", "--"],
        ["diff", "--name-only", "--no-renames", "-z", "--"],
        ["ls-files", "--others", "--exclude-standard", "-z"],
    ]
    paths: set[str] = set()
    try:
        for args in commands:
            result = _run_git(root, args)
            if result.returncode != 0:
                raise WorkspaceError(
                    "Git changed-file enumeration failed: "
                    + " ".join(args)
                )
            paths.update(_decode_nul_paths(result.stdout))
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkspaceError(f"cannot enumerate Git changed files: {exc}") from exc

    return {
        path
        for path in paths
        if path and not _excluded(path, installed_exclusions)
    }


def task_workspace_baseline(cwd: pathlib.Path) -> dict:
    """Capture enough Git state to attribute later final-content changes to a task."""
    root = git_root(cwd)
    if root is None:
        snapshot = filesystem_workspace_snapshot(cwd)
        return {
            "kind": "filesystem",
            "workspace_sha256": snapshot["sha256"],
        }

    head_result = _run_git(root, ["rev-parse", "HEAD"], text=True)
    head = head_result.stdout.strip() if head_result.returncode == 0 else None
    dirty_paths = sorted(_git_changed_paths(root))
    return {
        "kind": "git",
        "git_head": head,
        "dirty_files": {
            path: _working_file_state(root, path)
            for path in dirty_paths
        },
    }


def _git_committed_candidate_paths(
    root: pathlib.Path,
    base_head: str | None,
    current_head: str | None,
) -> set[str]:
    if base_head == current_head:
        return set()

    installed_exclusions = discovery_excluded_paths(root)
    if base_head and current_head:
        result = _run_git(
            root,
            [
                "diff",
                "--name-only",
                "--no-renames",
                "-z",
                base_head,
                current_head,
                "--",
            ],
        )
    elif current_head:
        result = _run_git(
            root,
            ["ls-tree", "-r", "--name-only", "-z", current_head],
        )
    else:
        return set()

    if result.returncode != 0:
        raise WorkspaceError("cannot enumerate committed task changes")

    return {
        path
        for path in _decode_nul_paths(result.stdout)
        if path and not _excluded(path, installed_exclusions)
    }


def task_changed_files(cwd: pathlib.Path, baseline: dict) -> dict:
    """Return paths whose final content differs from the prepared task baseline."""
    if baseline.get("kind") != "git":
        current = workspace_snapshot(cwd)
        return {
            "supported": False,
            "reason": "exact task changed-file attribution requires Git",
            "changed_files": [],
            "workspace_changed": (
                baseline.get("workspace_sha256") != current.get("sha256")
            ),
        }

    root = git_root(cwd)
    if root is None:
        raise WorkspaceError("prepared task used Git but repository is no longer a Git worktree")

    current_head_result = _run_git(root, ["rev-parse", "HEAD"], text=True)
    current_head = (
        current_head_result.stdout.strip()
        if current_head_result.returncode == 0
        else None
    )
    base_head = baseline.get("git_head")
    prepared_dirty = baseline.get("dirty_files") or {}
    if not isinstance(prepared_dirty, dict):
        raise WorkspaceError("invalid prepared task dirty-file baseline")

    candidates = set(prepared_dirty)
    candidates.update(_git_changed_paths(root))
    candidates.update(
        _git_committed_candidate_paths(root, base_head, current_head)
    )

    changed: list[str] = []
    for path in sorted(candidates):
        prepared_state = prepared_dirty.get(path)
        if prepared_state is None:
            prepared_state = (
                _git_ref_file_state(root, base_head, path)
                if base_head
                else "missing"
            )
        current_state = _working_file_state(root, path)
        if current_state != prepared_state:
            changed.append(path)

    return {
        "supported": True,
        "base_git_head": base_head,
        "current_git_head": current_head,
        "prepared_dirty_count": len(prepared_dirty),
        "candidate_count": len(candidates),
        "changed_files": changed,
    }
