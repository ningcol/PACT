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


def discovery_excluded_paths(root: pathlib.Path) -> set[str]:
    """Return installed PACT control-plane paths that are not project knowledge.

    Framework-managed files are always excluded. Project-owned seed files are
    excluded only while byte-identical to their installed default; once edited
    by the project they become discoverable project knowledge.
    """
    manifest_path = root / ".pact" / "install.json"
    if not manifest_path.is_file():
        return set()

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()

    files = manifest.get("files")
    if not isinstance(files, dict):
        return set()

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
        if not path.is_file() or not isinstance(expected, str):
            continue
        try:
            actual = sha256_file(path)
        except OSError:
            continue
        if actual == expected:
            excluded.add(relative)

    return excluded
