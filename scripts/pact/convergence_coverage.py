"""Mechanical coverage checks for task-scoped semantic Convergence."""

from __future__ import annotations

import hashlib
import pathlib


VALID_DISPOSITIONS = {
    "aligned",
    "updated",
    "removed",
    "stale",
    "owner-decision",
    "not-applicable",
}


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def review(
    context: dict,
    convergence: dict,
    *,
    root: pathlib.Path,
    context_path: pathlib.Path,
    expected_context_sha256: str | None = None,
) -> tuple[list[str], dict]:
    errors: list[str] = []

    current_context_sha256 = sha256_file(context_path)
    recorded_context_sha256 = convergence.get("context_sha256")

    if expected_context_sha256 is not None and current_context_sha256 != expected_context_sha256:
        errors.append(
            "current Task Context does not match prepared context "
            f"({current_context_sha256!r} != {expected_context_sha256!r})"
        )

    expected_binding = expected_context_sha256 or current_context_sha256
    if recorded_context_sha256 != expected_binding:
        errors.append(
            "convergence.context_sha256 does not match Task Context "
            f"({recorded_context_sha256!r} != {expected_binding!r})"
        )

    artifacts = context.get("artifacts", [])
    required_by_path: dict[str, dict] = {}
    context_duplicate_paths: list[str] = []
    for item in artifacts:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            continue
        path = item["path"]
        if path in required_by_path:
            context_duplicate_paths.append(path)
            errors.append(f"Task Context contains duplicate artifact path {path!r}")
            continue
        required_by_path[path] = item

    # Domain-first metadata is intentionally NOT promoted to applicable
    # authority during retrieval. But a task also must not silently finish
    # without considering the linked Rule/Decision sources. Require an
    # explicit Convergence disposition for each source-bound candidate.
    # Ordinary Context without scope_route retains its original behavior.
    routed_authority_paths: set[str] = set()
    routed_domain_paths: set[str] = set()
    scope = context.get("scope_route")
    if isinstance(scope, dict) and scope.get("status") == "unique":
        routed_domain_paths = {
            item["path"] for item in scope.get("domains", [])
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        }
        # A unique routed Domain is the source of its authority links. Older
        # or hand-edited Context packets that omitted it cannot complete even
        # if each metadata-only Rule/Decision hint has a disposition.
        for domain_path in sorted(routed_domain_paths):
            if domain_path not in required_by_path:
                errors.append(
                    f"Domain-first routed Domain missing from Task Context: {domain_path!r}; "
                    "reprepare the task with the confirmed Domain materialized"
                )
        candidates = scope.get("candidates")
        if not isinstance(candidates, list):
            errors.append("Domain-first candidate set is malformed")
        else:
            truncated = scope.get("truncated_candidates")
            if truncated or scope.get("total_candidates") != len(candidates):
                errors.append(
                    "Domain-first route has unlisted authority candidates; "
                    "review complete Domain sources and reprepare without "
                    "--scope-first before finishing"
                )
            for item in candidates:
                if not isinstance(item, dict):
                    errors.append("Domain-first candidate is malformed")
                    continue
                path = item.get("path")
                digest = item.get("sha256")
                if (not isinstance(path, str) or not path
                        or not isinstance(digest, str)
                        or len(digest) != 64
                        or any(ch not in "0123456789abcdef" for ch in digest)
                        or item.get("artifact_type") not in {"rule", "decision"}
                        or not isinstance(item.get("id"), str)):
                    errors.append("Domain-first candidate lacks valid source/authority binding")
                    continue
                if path in routed_authority_paths:
                    errors.append(f"duplicate Domain-first authority source {path!r}")
                    continue
                routed_authority_paths.add(path)
                if path in required_by_path:
                    existing = required_by_path[path]
                    if (existing.get("sha256") != digest
                            or existing.get("id") != item.get("id")
                            or existing.get("artifact_type") != item.get("artifact_type")):
                        errors.append(
                            f"Domain-first authority conflicts with selected Context source: {path!r}"
                        )
                else:
                    required_by_path[path] = item

    # Opt-in nonfunctional mode skips weak lexical Decision bodies, not
    # responsibility to consider previously recorded Owner decisions.
    # Otherwise task finish could treat an uninspected Decision as absent.
    # Apply source binding and explicit Convergence semantics as Domain-first.
    # Overflow must fail closed rather than certify a capped visible subset.
    deferred_decision_paths: set[str] = set()
    deferred = context.get("nonfunctional_decision_hints")
    if deferred is not None:
        items = deferred.get("candidates") if isinstance(deferred, dict) else None
        total = deferred.get("total_candidates") if isinstance(deferred, dict) else None
        truncated = (
            deferred.get("truncated_candidates")
            if isinstance(deferred, dict) else None
        )
        if (
            not isinstance(items, list)
            or type(total) is not int
            or type(truncated) is not int
            or total < 0 or truncated < 0
            or truncated > 0
            or total != len(items)
            or len(items) > 5
        ):
            errors.append(
                "Nonfunctional Context has unlisted or inconsistent Decision "
                "candidates; rerun without --nonfunctional and review complete "
                "Decision sources before finishing"
            )
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    errors.append("Nonfunctional Decision hint is malformed")
                    continue
                path, digest, ident = (
                    item.get("path"), item.get("sha256"), item.get("id")
                )
                if (
                    not isinstance(path, str) or not path
                    or not isinstance(ident, str)
                    or not ident.startswith("DEC-")
                    or not isinstance(digest, str)
                    or len(digest) != 64
                    or any(ch not in "0123456789abcdef" for ch in digest)
                ):
                    errors.append(
                        "Nonfunctional Decision hint lacks valid source/authority binding"
                    )
                    continue
                if path in deferred_decision_paths:
                    errors.append(
                        f"duplicate nonfunctional Decision source {path!r}"
                    )
                    continue
                deferred_decision_paths.add(path)
                if path in required_by_path:
                    original = required_by_path[path]
                    if (
                        original.get("sha256") != digest
                        or original.get("id") != ident
                        or original.get("artifact_type") != "decision"
                    ):
                        errors.append(
                            "Nonfunctional Decision hint conflicts with selected "
                            f"Task Context source: {path!r}"
                        )
                else:
                    required_by_path[path] = item

    coverage_by_path: dict[str, dict] = {}
    duplicate_paths: list[str] = []
    unknown_paths: list[str] = []

    for item in convergence.get("coverage", []):
        path = item.get("path")
        if path in coverage_by_path:
            duplicate_paths.append(path)
            errors.append(f"duplicate Convergence coverage entry for {path!r}")
            continue
        coverage_by_path[path] = item
        if path not in required_by_path:
            unknown_paths.append(path)
            errors.append(
                f"Convergence coverage references artifact not present in Task Context: {path!r}"
            )

    missing_paths = sorted(set(required_by_path) - set(coverage_by_path))
    for path in missing_paths:
        errors.append(
            f"Task Context artifact missing from Convergence coverage: {path!r}"
        )

    updated_verified: list[str] = []
    removed_verified: list[str] = []
    stale_paths: list[str] = []
    owner_decision_paths: list[str] = []

    for path, item in coverage_by_path.items():
        if path not in required_by_path:
            continue

        disposition = item.get("disposition")
        if disposition not in VALID_DISPOSITIONS:
            continue

        artifact = required_by_path[path]
        prepared_sha256 = artifact.get("sha256")
        current_path = (root / path).resolve()
        try:
            current_path.relative_to(root.resolve())
        except ValueError:
            errors.append(
                f"Task Context artifact escapes repository root: {path!r}"
            )
            continue
        current_exists = current_path.is_file()

        # Every prepared knowledge artifact is bound to original bytes, not
        # only opt-in Domain-first hints. An Agent must not edit a Decision and
        # simultaneously declare it aligned/not-applicable/stale.
        if disposition in {"aligned", "not-applicable", "stale"} and current_exists:
            if (
                not isinstance(prepared_sha256, str)
                or sha256_file(current_path) != prepared_sha256
            ):
                kind = (
                    "Routed Decision/Rule" if path in routed_authority_paths
                    else "Routed Domain" if path in routed_domain_paths
                    else "Deferred Decision" if path in deferred_decision_paths
                    else "Task Context knowledge"
                )
                errors.append(
                    f"{kind} changed since Task preparation: {path!r}; "
                    "review source changes and record an evidence-backed "
                    "updated/removed/owner-decision disposition"
                )

        if disposition == "updated":
            if not current_exists:
                errors.append(
                    f"Convergence marks {path!r} updated but artifact no longer exists; "
                    "use 'removed' for an intentional deletion"
                )
            elif not prepared_sha256:
                errors.append(
                    f"Convergence marks {path!r} updated without a prepared content SHA256"
                )
            elif sha256_file(current_path) == prepared_sha256:
                errors.append(
                    f"Convergence marks {path!r} updated but artifact content "
                    "matches the prepared Task Context"
                )
            else:
                updated_verified.append(path)

        elif disposition == "removed":
            if not prepared_sha256:
                errors.append(
                    f"Convergence marks {path!r} removed without a prepared content SHA256"
                )
            elif (root / path).is_symlink() or current_path.exists():
                errors.append(
                    f"Convergence marks {path!r} removed but artifact path still exists "
                    "or is a symlink"
                )
            else:
                removed_verified.append(path)

        elif not current_exists and disposition in {"aligned", "stale", "not-applicable"}:
            errors.append(
                f"Convergence marks {path!r} {disposition} but artifact no longer exists; "
                "use 'removed' for an intentional deletion or 'owner-decision' "
                "when deletion is unresolved"
            )

        if disposition == "stale":
            stale_paths.append(path)
        elif disposition == "owner-decision":
            owner_decision_paths.append(path)

    if owner_decision_paths and not any(
        finding.get("classification") == "owner-decision"
        for finding in convergence.get("findings", [])
    ):
        errors.append(
            "Convergence coverage contains owner-decision artifact(s) but "
            "no owner-decision finding provides the owner question"
        )

    stats = {
        "context_sha256": current_context_sha256,
        "required_artifacts": len(required_by_path),
        "routed_authority_paths": sorted(routed_authority_paths),
        "deferred_decision_paths": sorted(deferred_decision_paths),
        "covered_artifacts": len(
            set(required_by_path).intersection(coverage_by_path)
        ),
        "missing_artifacts": missing_paths,
        "unknown_artifacts": sorted(set(unknown_paths)),
        "duplicate_artifacts": sorted(
            set(duplicate_paths).union(context_duplicate_paths)
        ),
        "updated_verified": sorted(updated_verified),
        "removed_verified": sorted(removed_verified),
        "stale_artifacts": sorted(stale_paths),
        "owner_decision_artifacts": sorted(owner_decision_paths),
    }
    return errors, stats
