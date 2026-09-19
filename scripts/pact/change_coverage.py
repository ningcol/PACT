"""Mechanical coverage checks for task-scoped changed files."""

from __future__ import annotations


def review(
    convergence: dict,
    changed_files: list[str],
) -> tuple[list[str], dict]:
    errors: list[str] = []
    required = set(changed_files)
    coverage_by_path: dict[str, dict] = {}
    duplicates: list[str] = []

    raw = convergence.get("change_coverage", [])
    if raw is None:
        raw = []

    for item in raw:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if not isinstance(path, str):
            continue
        if path in coverage_by_path:
            duplicates.append(path)
            errors.append(
                f"duplicate Convergence change coverage entry for {path!r}"
            )
            continue
        coverage_by_path[path] = item

    covered = set(coverage_by_path)
    missing = sorted(required - covered)
    unknown = sorted(covered - required)

    for path in missing:
        errors.append(
            f"Task changed file missing from Convergence change coverage: {path!r}"
        )
    for path in unknown:
        errors.append(
            f"Convergence change coverage references file not changed by this task: {path!r}"
        )

    stats = {
        "required_changed_files": len(required),
        "covered_changed_files": len(required.intersection(covered)),
        "missing_changed_files": missing,
        "unknown_changed_files": unknown,
        "duplicate_changed_files": sorted(set(duplicates)),
    }
    return errors, stats
