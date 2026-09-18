"""Shared PACT distribution/install metadata helpers."""

from __future__ import annotations

import hashlib
import pathlib


FRAMEWORK_DOCS = [
    "docs/product/README.md",
    "docs/product/glossary/README.md",
    "docs/product/domains/README.md",
    "docs/product/domains/TEMPLATE.md",
    "docs/product/rules/README.md",
    "docs/product/rules/TEMPLATE.md",
    "docs/architecture/README.md",
    "docs/changes/README.md",
    "docs/changes/TEMPLATE.md",
    "docs/changes/active/README.md",
    "docs/changes/completed/README.md",
    "docs/changes/abandoned/README.md",
    "docs/drift/README.md",
    "docs/drift/TEMPLATE.md",
    "docs/drift/known/README.md",
    "docs/drift/resolved/README.md",
    "docs/drift/accepted/README.md",
    "docs/initialization.md",
    "docs/initialization-checklist.md",
    "docs/evaluation/pilot-scorecard.md",
    ".agents/decisions/README.md",
    ".agents/decisions/TEMPLATE.md",
    ".agents/decisions/proposed/README.md",
    ".agents/decisions/implemented/README.md",
    ".agents/decisions/rejected/README.md",
    ".agents/decisions/archived/README.md",
    ".pact/VERSION",
]

SEED_SOURCE_MAPPINGS = [
    (".pact/config.example.yaml", ".pact/config.yaml"),
    (".pact/baseline.example.yaml", ".pact/baseline.yaml"),
    (".pact/fitness.example.yaml", ".pact/fitness.yaml"),
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
    """Return files PACT may seed/manage in an adopted project.

    management=framework:
      may be upgraded automatically only when unchanged since the prior install.

    management=seed:
      project-owned after creation; never overwritten by upgrade.
    """
    entries: list[dict] = []

    def add(source_rel: str, target_rel: str | None = None, management: str = "framework") -> None:
        source = source_root / source_rel
        if not source.exists() or not source.is_file():
            return
        entries.append({
            "source": source,
            "source_path": source_rel,
            "target": pathlib.Path(target_rel or source_rel),
            "management": management,
        })

    for path in sorted((source_root / "docs" / "governance").glob("*.md")):
        entries.append({
            "source": path,
            "source_path": path.relative_to(source_root).as_posix(),
            "target": path.relative_to(source_root),
            "management": "seed",
        })

    for rel in FRAMEWORK_DOCS:
        add(rel)

    for path in sorted((source_root / ".agents" / "skills").glob("*.md")):
        entries.append({
            "source": path,
            "source_path": path.relative_to(source_root).as_posix(),
            "target": path.relative_to(source_root),
            "management": "seed",
        })

    for path in sorted((source_root / ".pact" / "schema").glob("*.json")):
        entries.append({
            "source": path,
            "source_path": path.relative_to(source_root).as_posix(),
            "target": path.relative_to(source_root),
            "management": "framework",
        })

    for path in sorted((source_root / "scripts" / "pact").iterdir()):
        if (
            path.is_file()
            and path.suffix in {".py", ".md", ".txt"}
            and path.name != "__pycache__"
        ):
            entries.append({
                "source": path,
                "source_path": path.relative_to(source_root).as_posix(),
                "target": path.relative_to(source_root),
                "management": "framework",
            })

    for source_rel, target_rel in SEED_SOURCE_MAPPINGS:
        add(source_rel, target_rel, management="seed")

    return entries


def github_actions_entry(source_root: pathlib.Path) -> dict | None:
    source_rel = ".pact/templates/github-actions/pact-project-check.yml"
    source = source_root / source_rel
    if not source.exists():
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
