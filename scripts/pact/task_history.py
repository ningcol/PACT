"""Local, audit-only snapshots of replaced task generations.

History never supplies current acceptance or execution evidence. The caller
holds the existing generation lock while publishing or rolling back a snapshot.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import uuid
from datetime import datetime, timezone

from protocol_ids import confined_state_root, validate_task_id


GENERATION = re.compile(r"^[0-9]{8}T[0-9]{12}Z-[0-9a-f]{12}$")


def history_root(root: pathlib.Path, task_id: str) -> pathlib.Path:
    validate_task_id(task_id)
    return confined_state_root(
        root, root / ".pact/tasks/.history" / task_id, field="task history"
    )


def _regular_tree(path: pathlib.Path) -> None:
    """Never follow archived aliases or read special files as task state."""
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"task history snapshot must be a real directory: {path}")
    for current, dirs, files in os.walk(path, followlinks=False):
        for name in dirs + files:
            item = pathlib.Path(current) / name
            if (item.is_symlink() or item.resolve() != item.absolute()
                    or not (item.is_file() or item.is_dir())):
                raise ValueError(f"unsafe task history snapshot entry: {item}")


def _read_manifest(path: pathlib.Path, task_id: str) -> dict:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"missing or invalid historical task manifest: {path}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise ValueError(f"cannot read historical task manifest {path}: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("task_id") != task_id:
        raise ValueError(f"invalid historical task identity: {path}")
    if manifest.get("status") not in {"prepared", "completed"}:
        raise ValueError(f"invalid historical task status: {path}")
    baseline = manifest.get("workspace_baseline", {})
    if not isinstance(baseline, dict):
        raise ValueError(f"invalid historical workspace baseline: {path}")
    return manifest


def stage_history(
    root: pathlib.Path, task_id: str, transaction: pathlib.Path,
    old_task: pathlib.Path, old_completion: pathlib.Path,
) -> tuple[pathlib.Path, pathlib.Path] | None:
    """Stage old local state; never copy runs or nest earlier history."""
    if not old_task.exists() and not old_completion.exists():
        return None
    parent = history_root(root, task_id)
    generation = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:12]
    destination = parent / generation
    staged = transaction / "history"
    staged.mkdir()
    for source in (old_task, old_completion):
        if source.exists():
            _regular_tree(source)
    manifest_path = old_task / "task.json"
    manifest = _read_manifest(manifest_path, task_id) if old_task.exists() else {}
    reference = manifest.get("completion_bundle", f".pact/completions/{task_id}")
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("invalid prior completion bundle reference")
    raw = pathlib.Path(reference).expanduser()
    selected = pathlib.Path(os.path.abspath(raw if raw.is_absolute() else root / raw))
    default = root / ".pact/completions" / task_id
    selected_default = selected == default
    external = not selected.is_relative_to(root)
    completion = old_completion if selected_default else selected
    if external:
        completion = None  # Preserve only the reference; never read external files.
    elif not selected_default:
        confined_state_root(root, selected, field="historical custom completion")
        protected = (root / ".pact/tasks", root / ".pact/tmp")
        if any(selected.is_relative_to(p) or p.is_relative_to(selected) for p in protected):
            raise ValueError("historical custom completion overlaps task or temporary state")
    sources = [("task", old_task), ("completion", completion)]
    if not selected_default:
        sources.append(("default-completion", old_completion))
    for name, source in sources:
        if source is None:
            continue
        if source.exists():
            _regular_tree(source)
            shutil.copytree(source, staged / name, symlinks=True)
    (staged / "archive.json").write_text(json.dumps({
        "completion_reference": reference,
        "external_completion_preserved": external,
    }) + "\n", encoding="utf-8")
    _regular_tree(staged)
    return staged, destination


def prior_generations(root: pathlib.Path, task_id: str, limit: int = 20) -> dict:
    """Return bounded historical metadata, without reinterpreting old receipts."""
    if not isinstance(limit, int) or not 1 <= limit <= 20:
        raise ValueError("task history limit must be between 1 and 20")
    folder = history_root(root, task_id)
    if not folder.exists():
        return {"items": [], "truncated": False}
    entries = sorted(folder.iterdir(), key=lambda p: p.name, reverse=True)
    # Validate names and directory identities even outside the output window;
    # do not silently turn corrupted/aliased history into 'no history'.
    for path in entries:
        if not GENERATION.fullmatch(path.name):
            raise ValueError(f"invalid task history generation: {path.name!r}")
        confined_state_root(root, path, field="task history generation")
    items = []
    for path in entries[:limit]:
        _regular_tree(path)
        task = path / "task/task.json"
        if task.exists():
            manifest = _read_manifest(task, task_id)
        elif (path / "task").exists():
            raise ValueError(f"missing historical task manifest: {task}")
        else:
            # A force preparation may replace orphaned completion state.
            manifest = {}
            if not (path / "completion").is_dir() and not (path / "default-completion").is_dir():
                raise ValueError(f"empty task history generation: {path}")
        archive_path = path / "archive.json"
        try:
            archive = json.loads(archive_path.read_text(encoding="utf-8")) if archive_path.exists() else {}
        except (OSError, ValueError) as exc:
            raise ValueError(f"invalid historical archive metadata: {archive_path}") from exc
        if not isinstance(archive, dict):
            raise ValueError(f"invalid historical archive metadata: {archive_path}")
        if archive_path.exists() and (
            not isinstance(archive.get("completion_reference"), str)
            or not archive["completion_reference"].strip()
            or not isinstance(archive.get("external_completion_preserved"), bool)
        ):
            raise ValueError(f"invalid historical archive metadata fields: {archive_path}")
        baseline = manifest.get("workspace_baseline", {})
        if not isinstance(baseline, dict):
            raise ValueError(f"invalid historical workspace baseline: {task}")
        items.append({
            "generation": path.name,
            "path": path.relative_to(root).as_posix(),
            "status": manifest.get("status"),
            "created_at": manifest.get("created_at"),
            "completed_at": manifest.get("completed_at"),
            "base_git_head": baseline.get("git_head"),
            "contract_sha256": manifest.get("contract_sha256"),
            "context_sha256": manifest.get("context_sha256"),
            "completion_present": (path / "completion").is_dir(),
            "completion_snapshot": (path / "completion").is_dir(),
            "completion_reference": archive.get("completion_reference", manifest.get("completion_bundle")),
            "external_completion_preserved": archive.get("external_completion_preserved", False),
        })
    return {"items": items, "truncated": len(entries) > limit}
