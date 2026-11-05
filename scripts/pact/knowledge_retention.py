"""Check the Agent's task-close knowledge-retention review inside Convergence.

The validator checks declared paths against the task delta when available. It
cannot decide that a new rule is authoritative or that a Decision is needed.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath


# Only PACT's normative/project-governance homes can be identified by path
# alone. Ordinary README/PRD updates may be retained voluntarily but must not
# be automatically classified as changes to normative Product Truth.
DURABLE_HOMES = (
    "docs/product/",
    "docs/architecture/",
    "docs/governance/",
    ".agents/decisions/",
)
DURABLE_FILES = frozenset({"AGENTS.md", ".pact/config.toml", ".pact/fitness.toml"})


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
    root: Path | None = None,
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
        declared = updated_set | created_set
        for path in sorted(declared - changed):
            errors.append(f"knowledge retention: declared path not changed by task: {path!r}")

        # The task-scoped review must not omit any changed canonical Rule,
        # Domain, Decision, Architecture, or governance file. The filesystem
        # does not tell us whether an ordinary README is an authoritative PRD,
        # so those remain explicitly Agent-reviewed rather than auto-promoted.
        canonical = {
            p for p in changed
            if p.startswith(DURABLE_HOMES) or p in DURABLE_FILES
        }
        unreported = sorted(canonical - declared)
        if unreported:
            errors.append(
                "knowledge retention: changed canonical knowledge paths "
                "not included in review: " + ", ".join(unreported[:8])
                + (" ..." if len(unreported) > 8 else "")
            )

    if root is not None:
        repository_root = root.resolve()
        for path in sorted(created_set):
            candidate = root / path
            resolved = candidate.resolve()
            if (
                not resolved.is_relative_to(repository_root)
                or candidate.is_symlink()
                or not candidate.is_file()
            ):
                errors.append(
                    f"knowledge retention: created knowledge file missing or unsafe: {path!r}"
                )

    return errors, {
        "status": "invalid" if errors else "reviewed",
        "disposition": disposition,
        "updated": sorted(updated_set),
        "created": sorted(created_set),
        "changed_paths_checked": changed_files is not None,
        "created_paths_checked": root is not None,
        "kind_of_change_verified": False,
        "semantic_verification": False,
    }
