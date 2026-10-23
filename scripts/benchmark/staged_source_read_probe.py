"""Source-bound downstream staged-reading diagnostic for PUBLIC pilot benchmarks.

Only benchmark instruments import this file. It is never an installed PACT
runtime feature or a model/Owner evidence pipeline. Frozen M0 remains intact.
"""
from __future__ import annotations

import hashlib
import pathlib
import re

from decision_memory_m0 import safe_file

def staged_source_read_receipt(
    target: pathlib.Path, selected: list[dict], current_ids: list[str],
) -> dict:
    """Measure source-verified downstream first-only vs all-Decision reads.

    The Context-selected ordering is frozen BEFORE any benchmark oracle is
    consulted. Physically inspect *all* selected sources to authenticate the
    counterfactual costs; do not claim this reduces benchmark-runner disk I/O.
    This is not semantic relevance, agent obedience or actual model tokens.
    """
    if (not isinstance(selected, list) or not isinstance(current_ids, list)
            or any(not isinstance(x, str) or not x.startswith("DEC-")
                   for x in current_ids)
            or len(set(current_ids)) != len(current_ids)):
        raise ValueError("staged read requires distinct current Decision IDs")
    current = set(current_ids)
    records: list[dict] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for item in selected:
        if not isinstance(item, dict):
            raise ValueError("staged read contains malformed Context artifact")
        ident = item.get("id")
        if ident not in current:
            continue
        relative = item.get("path")
        digest = item.get("sha256")
        if (item.get("artifact_type") != "decision"
                or not isinstance(relative, str)
                or not isinstance(digest, str)
                or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                or ident in seen_ids or relative in seen_paths):
            raise ValueError("staged Decision source identity or digest invalid")
        path = safe_file(target, relative)
        if not path.is_file():
            raise ValueError("staged Decision source is absent")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("staged Decision source changed after Context")
        # This is the exact same file-size-based estimator as installed Context.
        estimate = max((len(data) + 3) // 4, 1)
        supplied_estimate = item.get("estimated_tokens")
        if (supplied_estimate is not None
                and (type(supplied_estimate) is not int
                     or supplied_estimate != estimate)):
            raise ValueError("staged Decision source estimate differs from actual file")
        seen_ids.add(ident)
        seen_paths.add(relative)
        records.append({
            "id": ident, "path": relative, "sha256": digest,
            "read_source_bytes": len(data),
            "estimated_tokens_utf8_bytes_div4": estimate,
        })
    if seen_ids != current:
        raise ValueError("staged Context omitted a current Decision source")
    first = records[0] if records else None
    return {
        "policy": "first-current-Decision-only-vs-all-current-Decisions",
        "selected_current_ids_in_context_order": [x["id"] for x in records],
        "source_digest_verified": True,
        "all_current_source_bytes": sum(x["read_source_bytes"] for x in records),
        "first_only_source_bytes": first["read_source_bytes"] if first else 0,
        "all_current_estimated_tokens": sum(
            x["estimated_tokens_utf8_bytes_div4"] for x in records
        ),
        "first_only_estimated_tokens": (
            first["estimated_tokens_utf8_bytes_div4"] if first else 0
        ),
        "first_only_id": first["id"] if first else None,
        "unread_in_first_only": [x["id"] for x in records[1:]],
        "source_read_receipts": records,
        "model_calls": 0,
        "counterfactual_downstream_exposure_only": True,
    }



def score_staged_source_reads(reads: list[dict], expected: dict[str, list[str]]) -> dict:
    """Post-collection grade of frozen author-labelled primary retrieval only.

    Never use these labels to choose the first source. Even a clean 100% result
    cannot authorize omitting linked/cross-domain authority or Convergence.
    """
    if (len(reads) != len(expected)
            or len({row.get("id") for row in reads}) != len(reads)
            or set(row.get("id") for row in reads) != set(expected)):
        raise ValueError("staged source read denominator differs from frozen tasks")
    cases = []
    full_hits = first_hits = full_bytes = first_bytes = 0
    full_est = first_est = positives = negatives = 0
    for row in reads:
        ids = row.get("selected_current_ids_in_context_order")
        if (not isinstance(ids, list) or len(ids) != len(set(ids))
                or row.get("source_digest_verified") is not True
                or row.get("first_only_id") != (ids[0] if ids else None)):
            raise ValueError("staged read source order or integrity is invalid")
        want = expected[row["id"]]
        if not isinstance(want, list) or not all(isinstance(x, str) for x in want):
            raise ValueError("invalid staged author-labelled Decision target")
        full_found = set(want) & set(ids)
        first_found = set(want) & set(ids[:1])
        positives += len(want)
        negatives += not want
        full_hits += len(full_found)
        first_hits += len(first_found)
        full_bytes += row["all_current_source_bytes"]
        first_bytes += row["first_only_source_bytes"]
        full_est += row["all_current_estimated_tokens"]
        first_est += row["first_only_estimated_tokens"]
        cases.append({
            "id": row["id"], "target_count": len(want),
            "full_primary_hits": len(full_found),
            "first_primary_hits": len(first_found),
            "first_only_id": row["first_only_id"],
            "all_selected_decision_ids": ids,
            "unread_in_first_only": row["unread_in_first_only"],
            "full_source_bytes": row["all_current_source_bytes"],
            "first_source_bytes": row["first_only_source_bytes"],
        })
    return {
        "first_only_primary_hits": first_hits,
        "all_selected_primary_hits": full_hits,
        "author_labelled_primary_target_count": positives,
        "negative_case_count": negatives,
        "all_current_source_bytes": full_bytes,
        "first_only_source_bytes": first_bytes,
        "all_current_estimated_tokens": full_est,
        "first_only_estimated_tokens": first_est,
        "counterfactual_exposure_bytes_difference": full_bytes - first_bytes,
        "counterfactual_estimated_tokens_difference": full_est - first_est,
        "first_only_default": "NO-GO",
        "release_gate": "HOLD",
        "real_agent_evidence": False,
        "cases": cases,
    }

