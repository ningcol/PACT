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
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or ":" in value
        or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)
    ):
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
    verified_removed_paths: list[str] | None = None,
    prepared_paths: list[str] | None = None,
    prepared_file_states: dict[str, str] | None = None,
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
    # Optional for backwards compatibility. Removal of a durable record is
    # maintenance of existing knowledge, so "update" includes remove-only.
    removed = item.get("removed", [])
    if disposition == "pending":
        errors.append("knowledge retention: pending semantic review cannot complete")
    elif disposition not in {"none", "update", "create", "update-and-create"}:
        errors.append("knowledge retention: invalid disposition")
    if not isinstance(rationale, str) or not rationale.strip():
        errors.append("knowledge retention: nonblank rationale required")

    for name, paths in (("updated", updated), ("created", created), ("removed", removed)):
        if not isinstance(paths, list) or any(not _safe_path(p) for p in paths):
            errors.append(f"knowledge retention: {name} must contain safe repository paths")
        elif len(paths) != len(set(paths)):
            errors.append(f"knowledge retention: duplicate paths in {name}")
        elif any(not _knowledge_path(p) for p in paths):
            errors.append(f"knowledge retention: {name} must reference durable knowledge files")
    if errors:
        return errors, {"status": "invalid", "disposition": disposition}

    updated_set, created_set, removed_set = set(updated), set(created), set(removed)
    # Reuse already available source/baseline facts. Do not invoke Git or
    # retrieval merely to validate an ordinary `none` review. Missing proof
    # remains unknown; a file operation never proves first knowledge/authorship.
    known_existing = set(prepared_paths or [])
    known_missing = set()
    for path, state in (prepared_file_states or {}).items():
        if state == "missing":
            known_missing.add(path)
        elif isinstance(state, str):
            known_existing.add(path)
    for path in sorted(created_set & known_existing):
        errors.append(
            "knowledge retention: created path already existed at preparation; "
            "declare updated instead: " + repr(path)
        )
    for path in sorted(updated_set & known_missing):
        errors.append(
            "knowledge retention: updated path was absent at preparation; "
            "declare created instead: " + repr(path)
        )
    if (updated_set & created_set or updated_set & removed_set
            or created_set & removed_set):
        errors.append(
            "knowledge retention: a path cannot be updated, created, and/or removed in the same review"
        )

    expectations = {
        "none": (False, False),
        "update": (True, False),
        "create": (False, True),
        "update-and-create": (True, True),
    }
    if disposition in expectations:
        want_maintained, want_created = expectations[disposition]
        # A delete/rename replaces earlier durable knowledge and must be
        # explicitly reviewed; no extra disposition enum combinatorics.
        if (bool(updated_set | removed_set) != want_maintained
                or bool(created_set) != want_created):
            errors.append("knowledge retention: disposition conflicts with listed paths")

    if changed_files is not None:
        changed = set(changed_files)
        declared = updated_set | created_set | removed_set
        for path in sorted(declared - changed):
            errors.append(f"knowledge retention: declared path not changed by task: {path!r}")

        # The task-scoped review must not omit any changed canonical Rule,
        # Domain, Decision, Architecture, or governance file. The filesystem
        # does not tell us whether an ordinary README is an authoritative PRD,
        # so those remain explicitly Agent-reviewed rather than auto-promoted.
        canonical = {
            p for p in changed
            if (
                p in DURABLE_FILES
                or (p.startswith(DURABLE_HOMES) and p.endswith(".md"))
            )
        }
        unreported = sorted(canonical - declared)
        if unreported:
            prefix = (
                "knowledge retention: 'none' conflicts with changed durable knowledge paths: "
                if disposition == "none"
                else "knowledge retention: changed canonical knowledge paths not included in review: "
            )
            errors.append(
                prefix + ", ".join(unreported[:8])
                + (" ..." if len(unreported) > 8 else "")
            )

    if verified_removed_paths is not None:
        # Git attribution is optional for low-risk tasks without Git, but
        # Convergence still knows which prepared canonical sources disappeared.
        # A "none" claim must not hide a source-verified Rule/Decision removal.
        undeclared_removals = sorted(
            path for path in set(verified_removed_paths) - removed_set
            if (path in DURABLE_FILES
                or (path.startswith(DURABLE_HOMES) and path.endswith(".md")))
        )
        if undeclared_removals:
            errors.append(
                "knowledge retention: source-verified canonical removals "
                "not declared: " + ", ".join(undeclared_removals[:8])
            )

    if removed_set:
        # Reuse Convergence's existing source-bound "removed" coverage:
        # a deleted Rule/Decision must have been present in prepared Context,
        # with its original SHA and a verified removal. Merely typing its
        # name in this report never authorizes a deletion.
        covered = {
            row.get("path") for row in convergence.get("coverage", [])
            if isinstance(row, dict) and row.get("disposition") == "removed"
        }
        missing_coverage = sorted(removed_set - covered)
        if missing_coverage:
            errors.append(
                "knowledge retention: removed paths lack Convergence 'removed' coverage: "
                + ", ".join(missing_coverage[:8])
            )

        if verified_removed_paths is None:
            errors.append(
                "knowledge retention: removed paths require source-bound "
                "Task Context verification"
            )
        else:
            unverified = sorted(removed_set - set(verified_removed_paths))
            if unverified:
                errors.append(
                    "knowledge retention: removed paths are not source-verified: "
                    + ", ".join(unverified[:8])
                )

    if root is not None:
        repository_root = root.resolve()
        # Updated/created sources must exist; explicitly removed sources must
        # be absent and independently verified against a prepared Context.
        for path in sorted(updated_set | created_set | removed_set):
            candidate = root / path
            try:
                resolved = candidate.resolve(strict=False)
                # Reject leaf and parent symlinks, not only an eventual
                # escape; durable source identity must not be aliased.
                has_symlink = any(
                    (root.joinpath(*candidate.relative_to(root).parts[:i])).is_symlink()
                    for i in range(1, len(candidate.relative_to(root).parts) + 1)
                )
                safe = (
                    resolved.is_relative_to(repository_root)
                    and not has_symlink
                    and (not candidate.exists() if path in removed_set else candidate.is_file())
                )
            except (OSError, RuntimeError, ValueError):
                safe = False
            if not safe:
                errors.append(
                    "knowledge retention: declared knowledge file missing or unsafe: "
                    + repr(path)
                )

    return errors, {
        "status": "invalid" if errors else "reviewed",
        "disposition": disposition,
        "updated": sorted(updated_set),
        "created": sorted(created_set),
        "removed": sorted(removed_set),
        "changed_paths_checked": changed_files is not None,
        "created_paths_checked": root is not None,
        "kind_of_change_verified": bool(updated_set | created_set) and (
            updated_set <= known_existing and created_set <= known_missing
        ),
        "operation_kind_unknown": sorted(
            (updated_set - known_existing) | (created_set - known_missing)
        ),
        "operation_kind_interpretation": "File existence only; not knowledge novelty or authorship.",
        "removed_source_verified": bool(removed_set) and (
            verified_removed_paths is not None
            and removed_set.issubset(set(verified_removed_paths))
        ),
        "semantic_verification": False,
    }
