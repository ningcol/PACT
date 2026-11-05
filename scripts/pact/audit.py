#!/usr/bin/env python3
"""Produce a deterministic PACT repository health inventory."""

from __future__ import annotations

import argparse
import collections
import json
import itertools
import pathlib
import re
import subprocess
import sys

from discover import mixed_rule_authority
from runtime_exec import runtime_command

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_MAP = pathlib.Path(".pact/cache/project-map.json")



def _topic(doc: dict) -> str:
    """Stable low-noise signal; never a semantic conflict verdict."""
    title = str(doc.get("title") or "").casefold().strip()
    title = re.sub(r"^(?:rule|dec)-[a-z0-9-]+\s*[-—:：]\s*", "", title)
    title = re.sub(r"^decision\s*[:：]\s*", "", title)
    return re.sub(r"[\W_]+", "", title)


def _text_key(doc: dict) -> str:
    return re.sub(r"[\W_]+", "", str(doc.get("text") or "").casefold())


def _linked_decisions(a: dict, b: dict) -> bool:
    left, right = a.get("id"), b.get("id")
    return bool(
        (left and left in (b.get("supersedes") or []))
        or (right and right in (a.get("supersedes") or []))
        or (left and b.get("superseded_by") == left)
        or (right and a.get("superseded_by") == right)
    )


def _string_ids(value) -> set[str]:
    """Reject malformed metadata values without crashing or elevating them.

    The authoritative PACT check already rejects non-string IDs; Audit should
    remain a diagnostic inventory when Check fails, never treat untrusted
    values as valid graph edges or as a normal audit success.
    """
    if not isinstance(value, list):
        return set()
    return {
        value_id for value_id in value
        if isinstance(value_id, str) and value_id
    }


def _router_ids(router: dict) -> set[str]:
    """Only explicit machine IDs; arbitrary prose never becomes authority."""
    ids = _string_ids(router.get("related"))
    ids.update(re.findall(
        r"\b(?:RULE|DEC)-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*\b",
        str(router.get("text") or ""),
    ))
    return ids


def knowledge_review_candidates(docs: list[dict], *, domain: str | None = None) -> dict:
    """Generate bounded, review-only domain evidence; no automatic truth edits.

    Different prose can express the same policy, so this only detects strong
    structural/lexical overlaps. The scoped inventory lets an Agent check
    semantically different wording without calling all pairs conflicts.
    """
    domains = {
        d.get("id"): d for d in docs
        if d.get("artifact_type") == "domain" and isinstance(d.get("id"), str)
    }
    by_id = {
        d["id"]: d for d in docs
        if isinstance(d.get("id"), str)
    }
    if domain is not None and domain not in domains:
        raise ValueError(f"unknown Domain ID: {domain}")

    groups: dict[str, list[dict]] = {}
    for doc in docs:
        if doc.get("artifact_type") not in {"rule", "decision"}:
            continue
        if doc.get("status") not in {
            "candidate", "confirmed", "proposed", "implemented",
            "rejected", "superseded", "archived",
        }:
            continue
        for ident in sorted(_string_ids(doc.get("domains"))):
            if ident in domains and (domain is None or ident == domain):
                groups.setdefault(ident, []).append(doc)

    # Domain links may refer to legacy Decisions without a domains[] field.
    # Include them as review candidates, not automatically applicable authority.
    for ident, router in sorted(domains.items()):
        if domain is not None and ident != domain:
            continue
        seen = {d.get("path") for d in groups.get(ident, [])}
        for linked_id in sorted(_router_ids(router)):
            linked = by_id.get(linked_id)
            if (
                linked is not None
                and linked.get("artifact_type") in {"rule", "decision"}
                and linked.get("status") in {
                    "candidate", "confirmed", "proposed", "implemented",
                    "rejected", "superseded", "archived",
                }
                and linked.get("path") not in seen
            ):
                groups.setdefault(ident, []).append(linked)
                seen.add(linked["path"])

    candidates = []
    suppressed = 0
    comparisons_left = 5000
    overlap_scan_truncated = False
    for ident, members in sorted(groups.items()):
        for a, b in itertools.combinations(
            sorted(members, key=lambda d: str(d.get("path") or "")), 2
        ):
            if comparisons_left <= 0:
                overlap_scan_truncated = True
                break
            comparisons_left -= 1
            if a.get("artifact_type") != b.get("artifact_type"):
                continue
            if a.get("artifact_type") == "decision" and _linked_decisions(a, b):
                continue
            topic_a, topic_b = _topic(a), _topic(b)
            body_a, body_b = _text_key(a), _text_key(b)
            signal = None
            if topic_a == topic_b and (
                len(topic_a) >= 5
                or (len(topic_a) >= 2 and any("\u3400" <= c <= "\u9fff" for c in topic_a))
            ):
                signal = "same-title"
            elif body_a == body_b and len(body_a) >= 100:
                signal = "same-body"
            if signal:
                item = {
                    "domain": ident,
                    "paths": [a["path"], b["path"]],
                    "ids": [a.get("id"), b.get("id")],
                    "statuses": [a.get("status"), b.get("status")],
                    "signal": signal,
                    "reason": "review possible same-topic redundancy or contradiction; no semantic verdict",
                }
                if len(candidates) < 60:
                    candidates.append(item)
                else:
                    suppressed += 1
        if overlap_scan_truncated:
            break

    # A shared alias across confirmed Domains can route a request ambiguously.
    alias_pairs = []
    alias_suppressed = 0
    alias_sources: dict[str, list[str]] = {}
    for ident, d in sorted(domains.items()):
        if d.get("status") != "confirmed":
            continue
        aliases = d.get("aliases")
        for alias in aliases if isinstance(aliases, list) else []:
            if not isinstance(alias, str):
                continue
            norm = re.sub(r"\s+", " ", alias.casefold().strip())
            if len(norm) >= 2:
                alias_sources.setdefault(norm, []).append(ident)
    for alias, owners in sorted(alias_sources.items()):
        ids = sorted(set(owners))
        if len(ids) > 1 and (domain is None or domain in ids):
            item = {
                "alias": alias, "domains": ids,
                "reason": "same alias in distinct confirmed Domains; clarify retrieval meaning",
            }
            if len(alias_pairs) < 60:
                alias_pairs.append(item)
            else:
                alias_suppressed += 1

    scoped_sources = []
    if domain is not None:
        router = domains[domain]
        # Explicit ID references in the Domain router are hints, not approval.
        linked_ids = _router_ids(router)
        selected = {d["path"]: d for d in groups.get(domain, [])}
        for ident in linked_ids:
            d = by_id.get(ident)
            if d is not None and d.get("artifact_type") in {"rule", "decision"}:
                selected[d["path"]] = d
        scoped_sources = [{
            "id": d.get("id"), "path": d["path"],
            "artifact_type": d.get("artifact_type"),
            "status": d.get("status"),
            "routing_evidence": (
                "declared-domain" if domain in _string_ids(d.get("domains"))
                else "explicit-router-id"
            ),
        } for d in sorted(selected.values(), key=lambda d: d["path"])]

    total_scoped = len(scoped_sources)
    scoped_sources = scoped_sources[:100]

    return {
        "domain": domain,
        "domain_status": domains[domain].get("status") if domain else None,
        "possible_knowledge_overlaps": candidates,
        "overlap_candidates_suppressed": suppressed,
        "overlap_scan_truncated": overlap_scan_truncated,
        "domain_alias_collisions": alias_pairs,
        "alias_collisions_suppressed": alias_suppressed,
        "scoped_sources": scoped_sources,
        "scoped_sources_count": total_scoped,
        "scoped_sources_truncated": len(scoped_sources) < total_scoped,
    }


def build_map(root: pathlib.Path = ROOT) -> dict:
    output = root / DEFAULT_MAP
    result = subprocess.run(
        runtime_command(
            "map",
            "--output",
            str(output),
            "--ensure",
            root=root,
        ),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not output.is_file():
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "map failed"
        )
    return json.loads(output.read_text(encoding="utf-8"))


def evaluate(index: dict, *, deterministic_check: str, domain: str | None = None) -> dict:
    docs = index.get("documents", [])
    type_counts = collections.Counter(
        d.get("artifact_type", "document") for d in docs
    )
    status_counts = collections.Counter(
        f"{d.get('artifact_type')}:{d.get('status')}"
        for d in docs
        if d.get("status")
    )

    active_changes = [
        {"id": d.get("id"), "title": d["title"], "path": d["path"]}
        for d in docs
        if d.get("artifact_type") == "change"
        and d.get("status") == "active"
    ]
    known_drift = [
        {"id": d.get("id"), "title": d["title"], "path": d["path"]}
        for d in docs
        if d.get("artifact_type") == "drift"
        and d.get("status") == "known"
    ]

    semantic_review_targets = [
        {
            "reason": "active change should eventually converge and close",
            **item,
        }
        for item in active_changes
    ] + [
        {
            "reason": "known drift remains unresolved",
            **item,
        }
        for item in known_drift
    ]

    mixed_rule_candidates = [
        {
            "id": d.get("id"),
            "title": d.get("title"),
            "path": d.get("path"),
            "reason": (
                "confirmed rule contains explicitly unconfirmed heading(s); "
                "review and split by authority before treating the whole "
                "document as normative"
            ),
        }
        for d in docs
        if mixed_rule_authority(d)
    ]
    semantic_review_targets.extend(mixed_rule_candidates)

    # A superseded Decision remains useful history. Surface it for *semantic*
    # retention review; age/absence of backlinks never deletes engineering
    # rationale or changes its status automatically.
    decision_retention_candidates = [
        {
            "id": d.get("id"),
            "title": d.get("title"),
            "path": d.get("path"),
            "reason": (
                "explicitly superseded decision: review whether any current "
                "constraint still needs it; do not archive automatically"
            ),
        }
        for d in docs
        if d.get("artifact_type") == "decision"
        and d.get("status") == "superseded"
    ]
    semantic_review_targets.extend(decision_retention_candidates)

    domain_review = knowledge_review_candidates(docs, domain=domain)
    return {
        "deterministic_check": deterministic_check,
        **domain_review,
        "artifact_counts": dict(sorted(type_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "active_changes": active_changes,
        "known_drift": known_drift,
        "mixed_rule_candidates": mixed_rule_candidates,
        "decision_retention_candidates": decision_retention_candidates,
        "semantic_review_targets": semantic_review_targets,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit PACT repository health")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--domain", help="optional exact Domain ID for targeted read-only knowledge review")
    args = parser.parse_args()

    check = subprocess.run(
        runtime_command("check"),
        capture_output=True,
        text=True,
    )
    deterministic_check = "pass" if check.returncode == 0 else "fail"

    try:
        index = build_map(ROOT)
    except Exception as exc:
        print(f"PACT audit: cannot build project map: {exc}", file=sys.stderr)
        return 2

    try:
        result = evaluate(
            index,
            deterministic_check=deterministic_check,
            domain=args.domain,
        )
    except ValueError as exc:
        print(f"PACT audit: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"PACT audit: deterministic check = "
            f"{result['deterministic_check']}"
        )
        print("Artifact inventory:")
        for kind, count in sorted(result["artifact_counts"].items()):
            print(f"- {kind}: {count}")
        print(f"Active changes: {len(result['active_changes'])}")
        print(f"Known drift: {len(result['known_drift'])}")
        print(f"Mixed-authority rule candidates: {len(result['mixed_rule_candidates'])}")
        print(f"Decision retention review candidates: {len(result['decision_retention_candidates'])}")
        print(f"Possible same-domain knowledge overlaps: {len(result['possible_knowledge_overlaps'])}")
        print(f"Confirmed Domain alias collisions: {len(result['domain_alias_collisions'])}")
        if args.domain:
            print(f"Domain {args.domain} ({result['domain_status']}) review sources: {result['scoped_sources_count']}")
            if result["domain_status"] != "confirmed":
                print("WARNING: Domain is not confirmed; linked sources are review hints only")
            for item in result["scoped_sources"]:
                print(f"- {item['path']}: {item['artifact_type']} / {item['status']}")
            if result["scoped_sources_truncated"]:
                print("WARNING: scoped sources truncated; review the full Domain before completion")
        if result["overlap_scan_truncated"]:
            print("WARNING: overlap scan truncated at 5000 pairs; no completeness claim")
        for item in result["possible_knowledge_overlaps"]:
            print(f"- [{item['signal']}] {item['domain']}: {', '.join(item['paths'])} (review only)")
        for item in result["domain_alias_collisions"]:
            print(f"- alias {item['alias']!r}: {', '.join(item['domains'])} (review only)")
        if result["alias_collisions_suppressed"]:
            print("WARNING: extra alias collision candidates suppressed; scope by Domain")
        if result["semantic_review_targets"]:
            print("Semantic review targets:")
            for item in result["semantic_review_targets"]:
                label = item.get("id") or item["path"]
                print(f"- {label}: {item['reason']}")

    return 0 if check.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
