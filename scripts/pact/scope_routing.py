"""Optional, stdlib-only, explicit Domain-first knowledge router.

This router **locates** Domain and its cited authority. It never decides whether
a Rule or Decision is applicable: shared Domain, keywords and paths are evidence
of possible relevance, not Owner confirmation.
"""
from __future__ import annotations

import fnmatch
import json
import pathlib
import re

from cache import fingerprint_files
from discover import has_unspaced_script, document_tokens, document_term_matches
from map import FORMAT_VERSION, parse_document, source_paths, valid_project_index


DOMAIN_ID = re.compile(r"^DOMAIN-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
AUTHORITY_ID = re.compile(r"\b(?:DEC|RULE)-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
PATH_IN_TASK = re.compile(
    r"(?<![\w/])(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\b"
)
MAX_HINTS = 12


def _mixed_script_tokens(value: str) -> list[str]:
    """Split Latin/CJK adjacency before comparing declared compound names.

    Only Domain titles/aliases feed this matcher; code comments and arbitrary
    body strings are never Domain-routing authority.
    """
    separated: list[str] = []
    previous: str | None = None
    for ch in value:
        if (previous is not None and previous.isalnum() and ch.isalnum()
                and has_unspaced_script(previous) != has_unspaced_script(ch)):
            separated.append(" ")
        separated.append(ch)
        previous = ch
    return document_tokens("".join(separated))


def _mentions(text: str, name: str, *, compound: bool = False) -> bool:
    name = name.strip()
    if not name:
        return False
    # Domain aliases are *explicit* project-authored mappings; require a
    # word boundary for English names, not an arbitrary substring in login2.
    # Multi-character Han aliases remain usable without whitespace.
    has_cjk = has_unspaced_script(name)
    has_other_script = any(
        ch.isalnum() and not has_unspaced_script(ch) for ch in name
    )
    if compound and has_cjk and has_other_script:
        # A declared "Login認証" matches "login 認証", but not "login2 認証".
        # Compare the entire sequence after Latin/CJK and camel boundaries.
        required = _mixed_script_tokens(name)
        observed = _mixed_script_tokens(text)
        width = len(required)
        return width >= 2 and any(
            observed[pos:pos + width] == required
            for pos in range(len(observed) - width + 1)
        )
    if has_cjk:
        # Preserve unspaced Han, kana and hangul aliases unchanged.
        return len(name) >= 2 and name.casefold() in text.casefold()
    if re.search(r"(?<![\w])" + re.escape(name) + r"(?![\w])",
                 text, re.IGNORECASE):
        return True
    # Only project-declared MULTI-TOKEN title/alias names qualify for
    # compound matching. A generic one-token alias "login" must not turn
    # a task mentioning LoginRetry into an unrelated unique Domain route.
    return bool(compound and len(document_tokens(name)) >= 2
                and document_term_matches(name, text))


def _mentioned_paths(text: str) -> set[str]:
    return {
        match.group(0)
        for match in PATH_IN_TASK.finditer(text)
        if "://" not in text[max(0, match.start()-4):match.start()]
        and ".." not in pathlib.PurePosixPath(match.group(0)).parts
    }


def load_index(root: pathlib.Path) -> dict:
    """Reject an unverified index; source Markdown remains sole authority."""
    idx = root / ".pact" / "cache" / "project-map.json"
    if not idx.is_file() or idx.is_symlink():
        raise ValueError("Domain scope requires safely generated Project Map")
    data = json.loads(idx.read_text(encoding="utf-8"))
    paths, _ = source_paths(root)
    expected = {x.relative_to(root).as_posix() for x in paths}
    if (not isinstance(data, dict)
            or data.get("format_version") != FORMAT_VERSION
            or data.get("source_fingerprint") != fingerprint_files(root, paths)
            or not valid_project_index(data, expected_paths=expected)):
        raise ValueError("Domain scope Project Map stale or malformed")
    # The global map validator checks path uniqueness but historically permits
    # duplicate stable IDs. An ordinary cached document must never shadow a
    # verified Domain when its ID is reused, even if id_to_path was also forged.
    seen_ids: set[str] = set()
    for document in data["documents"]:
        ident = document.get("id")
        if ident:
            if ident in seen_ids:
                raise ValueError(f"Domain scope duplicate stable ID: {ident!r}")
            seen_ids.add(ident)
    # Index freshness and structure cannot authenticate metadata: a cache writer
    # could forge aliases/paths while retaining the original source fingerprint.
    # Reparse EVERY potential authority home (and any claimed authority artifact)
    # from actual Markdown and reject even a single inconsistent cached record.
    # Other ordinary documents retain their normal lightweight index semantics.
    checked_paths = {
        doc["path"]: doc for doc in data["documents"]
        if doc["path"].startswith((
            "docs/product/domains/", "docs/product/rules/",
            ".agents/decisions/",
        )) or doc["artifact_type"] in {"domain", "rule", "decision"}
    }
    for relative, cached in checked_paths.items():
        physical = root / relative
        if not physical.is_file() or physical.is_symlink():
            raise ValueError(f"Domain scope authority source unavailable: {relative!r}")
        if parse_document(physical, root) != cached:
            raise ValueError(f"Domain scope cached metadata differs from source: {relative!r}")
    if fingerprint_files(root, paths) != data["source_fingerprint"]:
        raise ValueError("Domain scope source changed during authority verification")
    return data


def resolve(task: str, index: dict) -> dict:
    """Return metadata-only scope hints from declared Domain IDs and paths."""
    documents = index.get("documents")
    if not isinstance(documents, list):
        raise ValueError("scope index documents must be a list")
    # Resolve Domain links only from Domain-home records, not from an unrelated
    # document with a colliding cached ID.
    by_id = {
        item["id"]: item for item in documents
        if isinstance(item, dict) and item.get("artifact_type") == "domain"
        and str(item.get("path", "")).startswith("docs/product/domains/")
        and isinstance(item.get("id"), str)
    }
    matching = []
    named_paths = _mentioned_paths(task)
    for doc in documents:
        if (not isinstance(doc, dict)
                or doc.get("artifact_type") != "domain"
                or not str(doc.get("path", "")).startswith("docs/product/domains/")
                or doc.get("status") != "confirmed"
                or not isinstance(doc.get("id"), str)
                or not DOMAIN_ID.fullmatch(doc["id"])):
            continue
        reasons = []
        if _mentions(task, doc["id"]):
            reasons.append("explicit stable Domain ID")
        if _mentions(task, str(doc.get("title") or ""), compound=True):
            reasons.append("declared Domain title")
        for alias in doc.get("aliases", []):
            if isinstance(alias, str) and _mentions(task, alias, compound=True):
                reasons.append("declared Domain alias")
                break
        for pattern in doc.get("paths", []):
            if (isinstance(pattern, str) and
                any(fnmatch.fnmatchcase(p, pattern) for p in named_paths)):
                reasons.append("explicit Domain code-path scope")
                break
        if reasons:
            matching.append({
                "id": doc["id"], "path": doc["path"],
                "title": doc["title"], "evidence": reasons,
            })

    matching.sort(key=lambda x: x["id"])
    state = "unique" if len(matching) == 1 else (
        "ambiguous" if matching else "unmapped"
    )
    references: list[dict] = []
    if matching:
        ids = {x["id"] for x in matching}
        # Only project-owned Domain descriptions and metadata can declare
        # links to other authority. Do not use arbitrary code comments.
        explicitly_linked = set()
        for domain in matching:
            source = by_id.get(domain["id"], {})
            explicitly_linked.update(
                r for r in source.get("related", [])
                if isinstance(r, str)
            )
            explicitly_linked.update(
                AUTHORITY_ID.findall(str(source.get("text") or ""))
            )
        for doc in documents:
            if not isinstance(doc, dict) or doc.get("artifact_type") not in {
                "rule", "decision"
            }:
                continue
            doc_id = doc.get("id")
            if not isinstance(doc_id, str) or not doc_id:
                continue
            via = []
            if any(d in ids for d in doc.get("domains", [])):
                via.append("declared authority Domain")
            if doc_id in explicitly_linked:
                via.append("explicit Domain reference")
            if via:
                references.append({
                    "id": doc_id, "path": doc["path"],
                    "artifact_type": doc["artifact_type"],
                    "status": doc.get("status") or "unknown",
                    "via": via,
                })
    references.sort(key=lambda x: (x["artifact_type"], x["id"]))
    return {
        "status": state,
        "domains": matching,
        # Internal full set: NEVER serialize into Context. Only the visible
        # candidate list is capped; explicit ID/title hits still have access
        # to the complete verified Domain-linked path set.
        "_all_candidate_paths": sorted({item["path"] for item in references}),
        "candidates": references[:MAX_HINTS],
        "total_candidates": len(references),
        "truncated_candidates": max(0, len(references) - MAX_HINTS),
        "applicability_verified": False,
    }


def route_only(
    task: str, root: pathlib.Path, *,
    index: dict | None = None
) -> dict:
    return resolve(task, index if index is not None else load_index(root))
