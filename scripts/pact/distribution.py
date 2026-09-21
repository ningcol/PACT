"""Shared PACT distribution/install metadata helpers."""

from __future__ import annotations

import hashlib
import json
import pathlib

from runtime_bundle import ensure_runtime_bundle


SEED_SOURCE_MAPPINGS = [
    (".pact/config.example.toml", ".pact/config.toml"),
    (".pact/baseline.example.toml", ".pact/baseline.toml"),
    (".pact/fitness.example.toml", ".pact/fitness.toml"),
]


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def runtime_version(source_root: pathlib.Path) -> str:
    path = source_root / ".pact" / "VERSION"
    if not path.exists():
        return "unknown"
    return path.read_text(encoding="utf-8").strip() or "unknown"


def source_manifest(source_root: pathlib.Path) -> list[dict]:
    """Return the single supported installed PACT surface."""
    entries: list[dict] = []

    def add(
        source_rel: str,
        target_rel: str | None = None,
        management: str = "framework",
    ) -> None:
        source = source_root / source_rel
        if not source.is_file():
            return
        entries.append({
            "source": source,
            "source_path": source_rel,
            "target": pathlib.Path(target_rel or source_rel),
            "management": management,
        })

    add("pact.py")
    add(".pact/VERSION")
    add("LICENSE", ".pact/LICENSE")
    add(".pact/templates/control-plane.gitignore", ".pact/.gitignore")

    runtime_bundle = ensure_runtime_bundle(source_root)
    entries.append({
        "source": runtime_bundle,
        "source_path": ".pact/pact.pyz",
        "target": pathlib.Path(".pact/pact.pyz"),
        "management": "framework",
    })

    for source_rel, target_rel in SEED_SOURCE_MAPPINGS:
        add(source_rel, target_rel, management="seed")

    return entries


def github_actions_entry(source_root: pathlib.Path) -> dict | None:
    source_rel = ".pact/templates/github-actions/pact-project-check.yml"
    source = source_root / source_rel
    if not source.is_file():
        return None
    return {
        "source": source,
        "source_path": source_rel,
        "target": pathlib.Path(".github/workflows/pact-project-check.yml"),
        "management": "framework",
    }


def manifest_record(entry: dict, destination: pathlib.Path) -> dict:
    source = entry.get("source")
    source_sha = sha256_file(source) if source and pathlib.Path(source).is_file() else None
    return {
        "management": entry["management"],
        "source_path": entry.get("source_path"),
        "source_sha256": source_sha,
        "installed_sha256": sha256_file(destination),
    }


def resolve_install_target(
    root: pathlib.Path,
    relative: str,
    *,
    allow_leaf_symlink: bool = False,
) -> pathlib.Path:
    """Resolve a tracked install path without allowing repository escapes."""
    if (
        not isinstance(relative, str)
        or not relative
        or "\\" in relative
        or ":" in relative
        or "\x00" in relative
    ):
        raise ValueError(f"unsafe tracked install path {relative!r}")

    pure = pathlib.PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"unsafe tracked install path {relative!r}")

    root_resolved = root.resolve()
    destination = root / pathlib.Path(*pure.parts)
    try:
        parent = destination.parent.resolve()
    except (OSError, RuntimeError) as exc:
        raise ValueError(
            f"cannot resolve tracked install path {relative!r}: {exc}"
        ) from exc

    if parent != root_resolved and root_resolved not in parent.parents:
        raise ValueError(
            f"tracked install path escapes repository through symlink: {relative!r}"
        )
    if destination.is_symlink() and not allow_leaf_symlink:
        raise ValueError(f"tracked install path is a symlink: {relative!r}")
    return destination


def read_install_manifest(root: pathlib.Path) -> dict | None:
    """Return a valid confined install manifest, None when absent, or raise."""
    root_resolved = root.resolve()
    path = root / ".pact" / "install.json"
    parent = path.parent.resolve()
    if parent != root_resolved and root_resolved not in parent.parents:
        raise ValueError(
            "invalid .pact/install.json: parent path escapes repository root"
        )
    if path.is_symlink():
        raise ValueError("invalid .pact/install.json: path must not be a symlink")
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid .pact/install.json: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("files"), dict):
        raise ValueError("invalid .pact/install.json: expected object with files map")
    if data.get("format_version") != 1:
        raise ValueError("invalid .pact/install.json: unsupported format_version")
    if not isinstance(data.get("runtime_version"), str) or not data["runtime_version"]:
        raise ValueError("invalid .pact/install.json: missing runtime_version")

    for relative, record in data["files"].items():
        try:
            resolve_install_target(
                root,
                relative,
                allow_leaf_symlink=(
                    isinstance(record, dict)
                    and record.get("management") == "seed"
                ),
            )
        except ValueError as exc:
            raise ValueError(f"invalid .pact/install.json: {exc}") from exc
        if not isinstance(record, dict):
            raise ValueError(
                f"invalid .pact/install.json: invalid record for {relative!r}"
            )
        if record.get("management") not in {"framework", "seed"}:
            raise ValueError(
                f"invalid .pact/install.json: invalid management for {relative!r}"
            )
        installed_sha = record.get("installed_sha256")
        if (
            not isinstance(installed_sha, str)
            or len(installed_sha) != 64
            or any(ch not in "0123456789abcdef" for ch in installed_sha)
        ):
            raise ValueError(
                f"invalid .pact/install.json: invalid installed_sha256 for {relative!r}"
            )

        source_sha = record.get("source_sha256")
        if source_sha is not None and (
            not isinstance(source_sha, str)
            or len(source_sha) != 64
            or any(ch not in "0123456789abcdef" for ch in source_sha)
        ):
            raise ValueError(
                f"invalid .pact/install.json: invalid source_sha256 for {relative!r}"
            )

        source_path = record.get("source_path")
        if source_path is not None and (
            not isinstance(source_path, str)
            or not source_path
            or "\\" in source_path
            or ":" in source_path
            or "\x00" in source_path
            or pathlib.PurePosixPath(source_path).is_absolute()
            or ".." in pathlib.PurePosixPath(source_path).parts
        ):
            raise ValueError(
                f"invalid .pact/install.json: unsafe source_path for {relative!r}"
            )
    return data


def discovery_excluded_paths(root: pathlib.Path) -> set[str]:
    """Return installed PACT control-plane paths that are not project knowledge.

    Framework-managed files are always excluded. Project-owned seed files are
    excluded only while byte-identical to their installed default; once edited
    by the project they become discoverable project knowledge.
    """
    manifest = read_install_manifest(root)
    if manifest is None:
        return set()
    files = manifest["files"]

    excluded: set[str] = set()
    for relative, record in files.items():
        if not isinstance(relative, str) or not isinstance(record, dict):
            continue

        management = record.get("management")
        if management == "framework":
            excluded.add(relative)
            continue
        if management != "seed":
            continue

        path = root / relative
        expected = record.get("installed_sha256")
        # A project replacing a seed with a symlink has changed ownership/state.
        # Do not follow the link merely to decide whether the seed is unchanged.
        if path.is_symlink() or not path.is_file() or not isinstance(expected, str):
            continue
        try:
            actual = sha256_file(path)
        except OSError:
            continue
        if actual == expected:
            excluded.add(relative)

    return excluded
