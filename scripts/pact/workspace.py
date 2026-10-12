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
    normalized = relative
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

        if not path.is_file():
            raise WorkspaceError(f"untracked path is not a regular file: {relative}")
        digest.update(b"executable\0" if path.stat().st_mode & 0o111 else b"regular\0")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\n")
    except OSError as exc:
        raise WorkspaceError(f"cannot fingerprint untracked file {relative}: {exc}") from exc


def _git_index_entry(root: pathlib.Path, relative: str) -> tuple[str, str] | None:
    """Get an exact indexed entry rather than expanding pathspec wildcards."""
    try:
        result = _run_git(
            root, ["ls-files", "--stage", "-z", "--", f":(literal){relative}"]
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkspaceError(f"cannot inspect Git index entry {relative}: {exc}") from exc
    if result.returncode != 0:
        raise WorkspaceError(f"cannot inspect Git index entry {relative}")

    found: tuple[str, str] | None = None
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        try:
            header, raw_path = record.split(b"\t", 1)
            mode, oid, stage = header.decode("ascii").split()
        except (ValueError, UnicodeError) as exc:
            raise WorkspaceError(f"malformed Git index entry {relative}") from exc
        if raw_path.decode("utf-8", errors="surrogateescape") != relative:
            continue
        if stage != "0" or found is not None:
            raise WorkspaceError(f"unmerged/ambiguous Git index entry {relative}")
        found = (mode, oid)
    return found


def _git_index_gitlinks(root: pathlib.Path) -> dict[str, str]:
    """Collect Git index entries of type gitlink (mode 160000)."""
    try:
        result = _run_git(root, ["ls-files", "--stage", "-z"])
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkspaceError(f"cannot enumerate Git submodules: {exc}") from exc
    if result.returncode != 0:
        raise WorkspaceError("cannot enumerate Git submodules")

    links: dict[str, str] = {}
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        try:
            header, raw_path = record.split(b"\t", 1)
            mode, oid, stage = header.decode("ascii").split()
        except (ValueError, UnicodeError) as exc:
            raise WorkspaceError("malformed Git index while identifying submodules") from exc
        if mode != "160000":
            continue
        relative = raw_path.decode("utf-8", errors="surrogateescape")
        if stage != "0" or relative in links:
            raise WorkspaceError(f"unmerged Git submodule: {relative}")
        links[relative] = oid
    return links


def _ensure_clean_gitlinks(root: pathlib.Path, seen: set[pathlib.Path] | None = None) -> None:
    """Refuse stable verification fingerprints for dirty or unknown gitlinks."""
    root = root.resolve()
    if seen is None:
        seen = set()
    if root in seen:
        raise WorkspaceError(f"repeated Git submodule worktree: {root}")
    seen.add(root)

    for relative, expected_sha in _git_index_gitlinks(root).items():
        child = root / relative
        if child.is_symlink() or not child.is_dir():
            raise WorkspaceError(f"Git submodule is missing/uninitialized: {relative}")
        resolved = child.resolve()
        if not resolved.is_relative_to(root) or git_root(child) != resolved:
            raise WorkspaceError(f"Git submodule is not a contained Git worktree: {relative}")

        try:
            head = _run_git(child, ["rev-parse", "HEAD"], text=True)
            status = _run_git(
                child,
                ["status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=none"],
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise WorkspaceError(f"cannot inspect Git submodule {relative}: {exc}") from exc
        if head.returncode != 0 or head.stdout.strip() != expected_sha:
            raise WorkspaceError(f"Git submodule HEAD differs from index: {relative}")
        if status.returncode != 0:
            raise WorkspaceError(f"cannot inspect Git submodule status: {relative}")
        if status.stdout:
            raise WorkspaceError(f"Git submodule has unverified workspace changes: {relative}")
        _ensure_clean_gitlinks(child, seen)


def _git_filemode_enabled(root: pathlib.Path) -> bool:
    try:
        result = _run_git(root, ["config", "--bool", "core.filemode"], text=True)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkspaceError(f"cannot inspect Git filemode policy: {exc}") from exc
    if result.returncode == 1:
        return os.name != "nt"
    if result.returncode != 0 or result.stdout.strip() not in {"true", "false"}:
        raise WorkspaceError("cannot inspect Git filemode policy")
    return result.stdout.strip() == "true"


def _git_symlinks_enabled(root: pathlib.Path) -> bool:
    try:
        result = _run_git(root, ["config", "--bool", "core.symlinks"], text=True)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkspaceError(f"cannot inspect Git symlink policy: {exc}") from exc
    if result.returncode == 1:
        return os.name != "nt"
    if result.returncode != 0 or result.stdout.strip() not in {"true", "false"}:
        raise WorkspaceError("cannot inspect Git symlink policy")
    return result.stdout.strip() == "true"


def _git_index_file_state(root: pathlib.Path, relative: str) -> str:
    try:
        result = _run_git(
            root,
            ["ls-files", "--stage", "-z", "--", f":(literal){relative}"],
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
    _ensure_clean_gitlinks(root)

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
    # V3 invalidates prior receipts when stronger Git file identity is in effect.
    digest.update(b"PACT-WORKSPACE-V3\n")
    digest.update(f"HEAD:{head or '<none>'}\n".encode())

    for relative in sorted(staged_paths):
        digest.update(b"STAGED\0")
        digest.update(relative.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        digest.update(_git_index_file_state(root, relative).encode("ascii"))
        digest.update(b"\n")

    filemode_enabled = _git_filemode_enabled(root) if unstaged_paths else None
    for relative in sorted(unstaged_paths):
        digest.update(b"UNSTAGED\0")
        digest.update(relative.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        digest.update(
            _working_file_state(root, relative, filemode_enabled=filemode_enabled).encode("ascii")
        )
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
        item.decode("utf-8", errors="surrogateescape")
        for item in data.split(b"\0")
        if item
    ]


def _working_file_state(
    root: pathlib.Path,
    relative: str,
    *,
    filemode_enabled: bool | None = None,
) -> str:
    """Comparable workspace file identity: type, Git execute bit, contents."""
    path = root / relative
    if path.is_symlink():
        payload = b"symlink\0" + os.readlink(path).encode(
            "utf-8", errors="surrogateescape"
        )
        return "symlink:sha256:" + hashlib.sha256(payload).hexdigest()

    entry = _git_index_entry(root, relative)
    index_mode = entry[0] if entry else None
    if path.is_dir():
        if index_mode != "160000":
            return "missing"
        try:
            head = _run_git(path, ["rev-parse", "HEAD"], text=True)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise WorkspaceError(f"cannot inspect Git submodule HEAD {relative}: {exc}") from exc
        if head.returncode != 0:
            raise WorkspaceError(f"cannot inspect Git submodule HEAD: {relative}")
        return "gitlink:" + head.stdout.strip()
    if not path.is_file():
        return "missing"
    if index_mode == "160000":
        raise WorkspaceError(f"Git submodule is not a directory: {relative}")

    if filemode_enabled is None:
        filemode_enabled = _git_filemode_enabled(root)
    digest = hashlib.sha256()
    try:
        actual_exec = bool(path.stat().st_mode & 0o111)
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise WorkspaceError(f"cannot hash workspace file {relative}: {exc}") from exc

    # Git with core.symlinks=false checks a tracked symlink out as text.
    if index_mode == "120000" and not _git_symlinks_enabled(root):
        return "symlink:sha256:" + hashlib.sha256(
            b"symlink\0" + path.read_bytes()
        ).hexdigest()

    executable = actual_exec if filemode_enabled else index_mode == "100755"
    return f"mode:{'111' if executable else '0'}:sha256:" + digest.hexdigest()


def _git_ref_file_state(root: pathlib.Path, ref: str, relative: str) -> str:
    """Read committed identity with the same type/mode/content encoding."""
    try:
        listing = _run_git(root, ["ls-tree", "-z", ref, "--", f":(literal){relative}"])
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkspaceError(f"cannot inspect prepared Git file {relative}: {exc}") from exc
    if listing.returncode != 0:
        raise WorkspaceError(f"cannot inspect prepared Git file {relative}")

    records = [record for record in listing.stdout.split(b"\0") if record]
    if not records:
        return "missing"
    if len(records) != 1:
        raise WorkspaceError(f"ambiguous Git tree path for {relative}")
    try:
        metadata, raw_path = records[0].split(b"\t", 1)
        mode, object_type, oid = metadata.decode("ascii").split()
    except (ValueError, UnicodeError) as exc:
        raise WorkspaceError(f"malformed Git tree entry for {relative}") from exc
    if raw_path.decode("utf-8", errors="surrogateescape") != relative:
        raise WorkspaceError(f"Git tree path did not match {relative}")

    if mode == "160000" and object_type == "commit":
        return "gitlink:" + oid
    if mode not in {"100644", "100755", "120000"} or object_type != "blob":
        raise WorkspaceError(f"unsupported Git file type for {relative}: {mode}")
    try:
        blob = _run_git(root, ["cat-file", "blob", oid])
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkspaceError(f"cannot read Git blob {relative}: {exc}") from exc
    if blob.returncode != 0:
        raise WorkspaceError(f"cannot read Git blob {relative}")

    if mode == "120000":
        return "symlink:sha256:" + hashlib.sha256(
            b"symlink\0" + blob.stdout
        ).hexdigest()
    return f"mode:{'111' if mode == '100755' else '0'}:sha256:" + hashlib.sha256(
        blob.stdout
    ).hexdigest()


def _compatible_prepared_state(state: str) -> str:
    """Normalize pre-V3 dirty-file baselines instead of inventing changes."""
    if state.startswith("mode:"):
        fields = state.split(":", 3)
        if len(fields) == 4 and fields[2] == "sha256":
            try:
                executable = bool(int(fields[1], 8))
            except ValueError as exc:
                raise WorkspaceError("invalid prepared Git file mode") from exc
            return f"mode:{'111' if executable else '0'}:sha256:" + fields[3]
    if state.startswith("sha256:"):
        # Old symlink identities hashed b"symlink\0" followed by target bytes.
        return "symlink:" + state
    return state


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

    _ensure_clean_gitlinks(root)
    head_result = _run_git(root, ["rev-parse", "HEAD"], text=True)
    head = head_result.stdout.strip() if head_result.returncode == 0 else None
    dirty_paths = sorted(_git_changed_paths(root))
    filemode_enabled = _git_filemode_enabled(root) if dirty_paths else None
    return {
        "kind": "git",
        "git_head": head,
        "dirty_files": {
            path: _working_file_state(root, path, filemode_enabled=filemode_enabled)
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

    _ensure_clean_gitlinks(root)
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
    filemode_enabled = _git_filemode_enabled(root) if candidates else None
    for path in sorted(candidates):
        prepared_state = prepared_dirty.get(path)
        if prepared_state is None:
            prepared_state = (
                _git_ref_file_state(root, base_head, path)
                if base_head
                else "missing"
            )
        current_state = _working_file_state(root, path, filemode_enabled=filemode_enabled)
        if not isinstance(prepared_state, str):
            raise WorkspaceError(f"invalid prepared Git file state for {path}")
        if current_state != _compatible_prepared_state(prepared_state):
            changed.append(path)

    return {
        "supported": True,
        "base_git_head": base_head,
        "current_git_head": current_head,
        "prepared_dirty_count": len(prepared_dirty),
        "candidate_count": len(candidates),
        "changed_files": changed,
    }
