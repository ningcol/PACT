#!/usr/bin/env python3
"""Deterministic lexical discovery over PACT project and optional code maps."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

from runtime_exec import runtime_command


ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_INDEX = ROOT / ".pact" / "cache" / "project-map.json"
DEFAULT_CODE_INDEX = ROOT / ".pact" / "cache" / "code-map.json"
RRF_K = 60
CONFIDENCE_ORDER = {
    "direct": 4,
    "relative-resolved": 3,
    "ast-resolved": 2,
    "heuristic": 1,
}


def norm(value: str) -> str:
    return value.casefold().strip()


def terms(query: str) -> list[str]:
    parts = re.findall(r"[\w\-]+", norm(query), flags=re.UNICODE)
    return [p for p in parts if p]


def normalize_queries(primary: str, extras: list[str] | None = None) -> list[str]:
    values = [primary, *(extras or [])]
    queries: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        key = norm(cleaned)
        if not cleaned or key in seen:
            continue
        seen.add(key)
        queries.append(cleaned)
    return queries


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


def score_code_file(item: dict, query: str) -> tuple[int, list[str]]:
    q = norm(query)
    ts = terms(query)
    path = norm(item.get("path", ""))
    name = norm(pathlib.PurePosixPath(item.get("path", "")).stem)
    symbols = [norm(x) for x in item.get("symbols", [])]
    imports = [norm(x.get("raw", "")) for x in item.get("imports", [])]

    score = 0
    reasons: list[str] = []

    if q and q == name:
        score += 140
        reasons.append("exact code file name")
    elif q and q in path:
        score += 85
        reasons.append("code path contains query")

    if q and q in symbols:
        score += 130
        reasons.append("exact symbol")
    elif q and any(q in symbol for symbol in symbols):
        score += 90
        reasons.append("symbol contains query")

    if q and any(q in raw for raw in imports):
        score += 45
        reasons.append("import text contains query")

    matched = 0
    for term in ts:
        term_score = 0
        if term in path:
            term_score = max(term_score, 18)
        if any(term in symbol for symbol in symbols):
            term_score = max(term_score, 25)
        if any(term in raw for raw in imports):
            term_score = max(term_score, 10)
        if term_score:
            matched += 1
            score += term_score

    if ts and matched == len(ts):
        score += 15
        reasons.append("all query terms matched in code metadata")

    return score, reasons


def ensure_index(path: pathlib.Path) -> None:
    subprocess.run(
        runtime_command("map", "--output", str(path), "--ensure"),
        check=True,
        stdout=subprocess.DEVNULL,
    )


def ensure_code_index(path: pathlib.Path) -> None:
    subprocess.run(
        runtime_command("code-map", "--output", str(path), "--ensure"),
        check=True,
        stdout=subprocess.DEVNULL,
    )


def ranked_knowledge_results(index: dict, query: str, limit: int) -> list[dict]:
    ranked = []
    for doc in index.get("documents", []):
        score, reasons = score_document(doc, query)
        if score <= 0:
            continue
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
            "verification": doc.get("verification", []),
        })
    ranked.sort(key=lambda x: (-x["score"], x["path"]))
    return ranked[: max(limit, 1)]


def ranked_code_results(code_index: dict, query: str, limit: int) -> list[dict]:
    direct = []
    for item in code_index.get("files", []):
        score, reasons = score_code_file(item, query)
        if score > 0:
            direct.append({
                "score": score,
                "reasons": reasons,
                "path": item["path"],
                "language": item["language"],
                "is_test": item["is_test"],
                "symbols": item.get("symbols", []),
                "relation": "direct-match",
                "confidence": "direct",
            })

    direct.sort(key=lambda x: (-x["score"], x["path"]))
    direct = direct[: max(limit, 1)]

    if not direct:
        return []

    direct_paths = {item["path"] for item in direct}
    neighbor_scores: dict[str, int] = {}
    neighbor_reasons: dict[str, set[str]] = {}

    for edge in code_index.get("edges", []):
        if edge["from"] in direct_paths and edge["to"] not in direct_paths:
            confidence = edge.get("confidence", "heuristic")
            base = {
                "relative-resolved": 35,
                "ast-resolved": 32,
                "heuristic": 24,
            }.get(confidence, 20)
            neighbor_scores[edge["to"]] = max(
                neighbor_scores.get(edge["to"], 0), base
            )
            neighbor_reasons.setdefault(edge["to"], set()).add(
                f"imported by direct match {edge['from']} ({confidence})"
            )
        if edge["to"] in direct_paths and edge["from"] not in direct_paths:
            confidence = edge.get("confidence", "heuristic")
            base = {
                "relative-resolved": 40,
                "ast-resolved": 37,
                "heuristic": 28,
            }.get(confidence, 24)
            neighbor_scores[edge["from"]] = max(
                neighbor_scores.get(edge["from"], 0), base
            )
            neighbor_reasons.setdefault(edge["from"], set()).add(
                f"imports direct match {edge['to']} ({confidence})"
            )

    by_path = {item["path"]: item for item in code_index.get("files", [])}
    neighbors = []
    for path, score in neighbor_scores.items():
        item = by_path.get(path)
        if not item:
            continue
        if item.get("is_test"):
            score += 10
        neighbors.append({
            "score": score,
            "reasons": sorted(neighbor_reasons[path]),
            "path": path,
            "language": item["language"],
            "is_test": item["is_test"],
            "symbols": item.get("symbols", []),
            "relation": "import-neighbor",
            "confidence": next(
                (
                    edge.get("confidence")
                    for edge in code_index.get("edges", [])
                    if (
                        (edge["from"] == path and edge["to"] in direct_paths)
                        or (edge["to"] == path and edge["from"] in direct_paths)
                    )
                ),
                "heuristic",
            ),
        })

    neighbors.sort(key=lambda x: (-x["score"], x["path"]))

    # code-limit is a final output budget, not a per-class budget. Keep a
    # small graph-neighbor share when available so structural context does not
    # disappear merely because lexical matches filled the candidate list.
    final_limit = max(limit, 1)
    if not neighbors:
        return direct[:final_limit]

    neighbor_budget = min(
        len(neighbors),
        max(1, final_limit // 3),
    )
    direct_budget = max(final_limit - neighbor_budget, 0)
    selected = direct[:direct_budget] + neighbors[:neighbor_budget]

    # If one class cannot use its share, fill the remaining budget from the
    # other class deterministically.
    selected_paths = {item["path"] for item in selected}
    if len(selected) < final_limit:
        remainder = [
            item
            for item in [*direct, *neighbors]
            if item["path"] not in selected_paths
        ]
        selected.extend(remainder[: final_limit - len(selected)])

    return selected[:final_limit]


def fuse_ranked_results(
    query_results: list[tuple[str, list[dict]]],
    limit: int,
) -> list[dict]:
    """Fuse ranked lists with deterministic RRF plus bounded query diversity."""
    final_limit = max(limit, 1)
    fused: dict[str, dict] = {}

    for query, results in query_results:
        for rank, item in enumerate(results, start=1):
            path = item.get("path")
            if not path:
                continue

            entry = fused.get(path)
            if entry is None:
                entry = {
                    **item,
                    "_rrf": 0,
                    "_max_score": int(item.get("score", 0)),
                    "_queries": [],
                    "_reasons": [],
                }
                fused[path] = entry

            entry["_rrf"] += round(1_000_000 / (RRF_K + rank))
            entry["_max_score"] = max(
                entry["_max_score"],
                int(item.get("score", 0)),
            )
            if query not in entry["_queries"]:
                entry["_queries"].append(query)

            for reason in item.get("reasons", []):
                decorated = f"{query}: {reason}"
                if decorated not in entry["_reasons"]:
                    entry["_reasons"].append(decorated)

            if item.get("relation") == "direct-match":
                entry["relation"] = "direct-match"
                entry["confidence"] = "direct"
            elif "confidence" in item:
                current_confidence = entry.get("confidence", "heuristic")
                incoming = item.get("confidence", "heuristic")
                if (
                    CONFIDENCE_ORDER.get(incoming, 0)
                    > CONFIDENCE_ORDER.get(current_confidence, 0)
                ):
                    entry["confidence"] = incoming

    rendered: dict[str, dict] = {}
    for path, entry in fused.items():
        result = {
            key: value
            for key, value in entry.items()
            if not key.startswith("_")
        }
        result["score"] = entry["_rrf"] * 1000 + entry["_max_score"]
        result["reasons"] = [
            f"matched query: {query}" for query in entry["_queries"]
        ] + entry["_reasons"]
        rendered[path] = result

    global_ranked = sorted(
        rendered.values(),
        key=lambda item: (-item["score"], item["path"]),
    )

    # Reserve at most half the final budget for per-query representation.
    # This is intentionally small: it prevents a specialized query from being
    # completely starved while leaving at least half the budget for global RRF.
    query_count = len(query_results)
    reserve_per_query = (
        final_limit // (2 * query_count)
        if query_count
        else 0
    )

    selected_paths: set[str] = set()
    if reserve_per_query:
        for _, results in query_results:
            taken = 0
            for item in results:
                path = item.get("path")
                if not path or path in selected_paths:
                    continue
                selected_paths.add(path)
                taken += 1
                if taken >= reserve_per_query:
                    break

    for item in global_ranked:
        if len(selected_paths) >= final_limit:
            break
        selected_paths.add(item["path"])

    selected = [
        rendered[path]
        for path in selected_paths
        if path in rendered
    ]
    selected.sort(key=lambda item: (-item["score"], item["path"]))
    return selected[:final_limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover PACT project knowledge")
    parser.add_argument("query", help="primary discovery query")
    parser.add_argument(
        "--query",
        dest="extra_queries",
        action="append",
        default=[],
        help="additional discovery query; repeat for multi-query fusion",
    )
    parser.add_argument("--index", default=str(DEFAULT_INDEX))
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument(
        "--code",
        action="store_true",
        help="also search generated code relationships",
    )
    parser.add_argument("--code-index", default=str(DEFAULT_CODE_INDEX))
    parser.add_argument("--code-limit", type=int, default=8)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    queries = normalize_queries(args.query, args.extra_queries)

    index_path = pathlib.Path(args.index)
    if not index_path.is_absolute():
        index_path = ROOT / index_path

    ensure_index(index_path)
    index = json.loads(index_path.read_text(encoding="utf-8"))

    knowledge_lists = [
        (
            query,
            ranked_knowledge_results(index, query, args.limit),
        )
        for query in queries
    ]
    if len(queries) == 1:
        ranked = knowledge_lists[0][1]
    else:
        ranked = fuse_ranked_results(knowledge_lists, args.limit)

    code_results = []
    if args.code:
        code_index_path = pathlib.Path(args.code_index)
        if not code_index_path.is_absolute():
            code_index_path = ROOT / code_index_path
        ensure_code_index(code_index_path)
        code_index = json.loads(code_index_path.read_text(encoding="utf-8"))

        if len(queries) == 1:
            code_results = ranked_code_results(
                code_index,
                queries[0],
                args.code_limit,
            )
        else:
            # Fusion may inspect a wider candidate pool, but the final result
            # is always capped by the requested code budget.
            candidate_limit = max(
                args.code_limit * 2,
                args.code_limit + len(queries),
            )
            code_lists = [
                (
                    query,
                    ranked_code_results(
                        code_index,
                        query,
                        candidate_limit,
                    ),
                )
                for query in queries
            ]
            code_results = fuse_ranked_results(
                code_lists,
                args.code_limit,
            )

    result = {
        "query": args.query,
        "queries": queries,
        "query_count": len(queries),
        "result_count": len(ranked),
        "results": ranked,
        "code_result_count": len(code_results),
        "code_results": code_results,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if not ranked and not code_results:
        print(f"PACT discovery: no matches for {queries!r}")
        return 1

    print(
        f"PACT discovery: {len(ranked)} knowledge match(es), "
        f"{len(code_results)} code match(es) from {len(queries)} query(s)"
    )
    if len(queries) > 1:
        for query in queries:
            print(f"- query: {query}")

    for item in ranked:
        ident = f" [{item['id']}]" if item.get("id") else ""
        print(
            f"- {item['title']}{ident} — {item['artifact_type']} — "
            f"{item['path']} (score {item['score']})"
        )
        if item["reasons"]:
            print(f"  why: {', '.join(item['reasons'])}")

    if code_results:
        print("Code:")
        for item in code_results:
            marker = "test" if item["is_test"] else item["language"]
            print(
                f"- {item['path']} — {marker} — "
                f"{item['relation']} (score {item['score']})"
            )
            if item["reasons"]:
                print(f"  why: {', '.join(item['reasons'])}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
