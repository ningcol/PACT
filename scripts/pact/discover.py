#!/usr/bin/env python3
"""Deterministic lexical discovery over the generated PACT project map."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_INDEX = ROOT / ".pact" / "cache" / "project-map.json"


def norm(value: str) -> str:
    return value.casefold().strip()


def terms(query: str) -> list[str]:
    parts = re.findall(r"[\w\-]+", norm(query), flags=re.UNICODE)
    return [p for p in parts if p]


def score_document(doc: dict, query: str) -> tuple[int, list[str]]:
    q = norm(query)
    ts = terms(query)
    score = 0
    reasons: list[str] = []

    ident = norm(str(doc.get("id") or ""))
    title = norm(str(doc.get("title") or ""))
    aliases = [norm(str(x)) for x in doc.get("aliases", [])]
    domains = [norm(str(x)) for x in doc.get("domains", [])]
    body = norm(str(doc.get("text") or ""))

    if ident and q == ident:
        score += 200
        reasons.append("exact stable id")

    if q and q == title:
        score += 140
        reasons.append("exact title")
    elif q and q in title:
        score += 90
        reasons.append("title contains query")

    if q and q in aliases:
        score += 130
        reasons.append("exact alias")
    elif q and any(q in alias for alias in aliases):
        score += 80
        reasons.append("alias contains query")

    if q and q in domains:
        score += 90
        reasons.append("exact domain")

    if q and q in body:
        score += 45
        reasons.append("body contains query")

    matched_terms = 0
    for term in ts:
        term_score = 0
        if term == ident:
            term_score = max(term_score, 80)
        if term in title:
            term_score = max(term_score, 30)
        if any(term in alias for alias in aliases):
            term_score = max(term_score, 35)
        if any(term in domain for domain in domains):
            term_score = max(term_score, 30)
        if term in body:
            term_score = max(term_score, 8)
        if term_score:
            matched_terms += 1
            score += term_score

    if ts and matched_terms == len(ts):
        score += 20
        reasons.append("all query terms matched")

    return score, reasons


def ensure_index(path: pathlib.Path) -> None:
    if path.exists():
        return
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "pact" / "map.py"), "--output", str(path)],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover PACT project knowledge")
    parser.add_argument("query")
    parser.add_argument("--index", default=str(DEFAULT_INDEX))
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    index_path = pathlib.Path(args.index)
    if not index_path.is_absolute():
        index_path = ROOT / index_path

    ensure_index(index_path)
    index = json.loads(index_path.read_text(encoding="utf-8"))

    ranked = []
    for doc in index.get("documents", []):
        score, reasons = score_document(doc, args.query)
        if score > 0:
            ranked.append({
                "score": score,
                "reasons": reasons,
                "id": doc.get("id"),
                "artifact_type": doc.get("artifact_type"),
                "title": doc.get("title"),
                "path": doc.get("path"),
                "status": doc.get("status"),
                "domains": doc.get("domains", []),
                "related": doc.get("related", []),
            })

    ranked.sort(key=lambda x: (-x["score"], x["path"]))
    ranked = ranked[: max(args.limit, 1)]

    result = {
        "query": args.query,
        "result_count": len(ranked),
        "results": ranked,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if not ranked:
        print(f"PACT discovery: no matches for {args.query!r}")
        return 1

    print(f"PACT discovery: {len(ranked)} match(es) for {args.query!r}")
    for item in ranked:
        ident = f" [{item['id']}]" if item.get("id") else ""
        print(
            f"- {item['title']}{ident} — {item['artifact_type']} — "
            f"{item['path']} (score {item['score']})"
        )
        if item["reasons"]:
            print(f"  why: {', '.join(item['reasons'])}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
