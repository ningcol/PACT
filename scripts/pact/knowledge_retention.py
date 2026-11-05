"""Check the Agent's task-close knowledge-retention review inside Convergence.

The validator checks declared paths against the task delta when available. It
cannot decide that a new rule is authoritative or that a Decision is needed.
"""

from __future__ import annotations

from pathlib import PurePosixPath


DURABLE_HOMES = (
    "docs/product/domains/",
    "docs/product/rules/",
    "docs/architecture/",
    ".agents/decisions/",
)


def _safe_path(value: str) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        return False
    return (
        not value.startswith("/")
        and all(part not in {"", ".", ".."} for part in value.split("/"))
        and str(PurePosixPath(value)) == value
    )


def _knowledge_path(path: str) -> bool:
    """Prevent source code/tests from being mislabelled as durable knowledge."""
    # Ordinary project documentation can live outside docs/ (for example
    # product/requirements/, README.md or .agents/decisions/). Do not force
    # users to relocate their existing business documents.
    return (
        (path.endswith(".md") and not path.startswith((".pact/", ".git/")))
        or path in {".pact/config.toml", ".pact/fitness.toml"}
    )


def review(
    convergence: dict,
    *,
    changed_files: list[str] | None = None,
    require: bool = False,
) -> tuple[list[str], dict]:
    """Review optional knowledge disposition; legacy reports remain readable."""
    item = convergence.get("knowledge_retention")
    if item is None:
        return (
            ["knowledge retention: explicit Convergence review required"] if require else [],
            {"status": "unreviewed", "disposition": None},
        )

    if not isinstance(item, dict):
        return ["knowledge retention: expected an object"], {"status": "invalid"}

    errors: list[str] = []
    disposition = item.get("disposition")
    rationale = item.get("rationale")
    updated = item.get("updated")
    created = item.get("created")
    if disposition == "pending":
        errors.append("knowledge retention: pending semantic review cannot complete")
    elif disposition not in {"none", "update", "create", "update-and-create"}:
        errors.append("knowledge retention: invalid disposition")
    if not isinstance(rationale, str) or not rationale.strip():
        errors.append("knowledge retention: nonblank rationale required")

    for name, paths in (("updated", updated), ("created", created)):
        if not isinstance(paths, list) or any(not _safe_path(p) for p in paths):
            errors.append(f"knowledge retention: {name} must contain safe repository paths")
        elif len(paths) != len(set(paths)):
            errors.append(f"knowledge retention: duplicate paths in {name}")
        elif any(not _knowledge_path(p) for p in paths):
            errors.append(f"knowledge retention: {name} must reference durable knowledge files")
    if errors:
        return errors, {"status": "invalid", "disposition": disposition}

    updated_set, created_set = set(updated), set(created)
    if updated_set & created_set:
        errors.append("knowledge retention: a path cannot be both updated and created")

    expectations = {
        "none": (False, False),
        "update": (True, False),
        "create": (False, True),
        "update-and-create": (True, True),
    }
    if disposition in expectations:
        want_updated, want_created = expectations[disposition]
        if bool(updated_set) != want_updated or bool(created_set) != want_created:
            errors.append("knowledge retention: disposition conflicts with listed paths")

    if changed_files is not None:
        changed = set(changed_files)
        for path in sorted((updated_set | created_set) - changed):
            errors.append(f"knowledge retention: declared path not changed by task: {path!r}")
        if disposition == "none":
            durable_changes = sorted(p for p in changed if p.startswith(DURABLE_HOMES))
            if durable_changes:
                errors.append(
                    "knowledge retention: 'none' conflicts with changed durable "
                    "knowledge paths: " + ", ".join(durable_changes[:8])
                )

    return errors, {
        "status": "invalid" if errors else "reviewed",
        "disposition": disposition,
        "updated": sorted(updated_set),
        "created": sorted(created_set),
        "changed_paths_checked": changed_files is not None,
        "semantic_verification": False,
    }
