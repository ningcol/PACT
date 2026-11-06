"""Bounded task-local knowledge reuse hints; no index, scan, or authority edits."""

from __future__ import annotations

import hashlib
import itertools
import pathlib
import posixpath
import re
import stat
from urllib.parse import unquote, urlsplit

from audit import overlap_signal
from formats import parse_markdown_metadata
from knowledge_retention import DURABLE_HOMES, _safe_path, review as review_retention


MAX_FILES = 80
MAX_FILE_BYTES = 128 * 1024
MAX_TOTAL_BYTES = 512 * 1024
MAX_PAIRS = 2000
MAX_HINTS = 60
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _scope(body: str) -> str | None:
    match = re.search(
        r"^##\s+(?:Scope|Applicability|Applies to|适用范围|适用条件|适用于)\s*\n(.*?)(?=^##\s|\Z)",
        body, re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()[:512]
    inline = re.search(
        r"^>\s*\*\*(?:适用范围|适用条件|适用于|Scope|Applies to)\*\*\s*[:：]\s*(.+)$",
        body, re.MULTILINE | re.IGNORECASE,
    )
    return inline.group(1).strip()[:512] if inline else None


def review(root: pathlib.Path, context: dict, convergence: dict | None,
           task_change: dict, baseline: dict) -> dict:
    """Read only task outputs, prepared Markdown, and their explicit links.

    This is intentionally incomplete. It cannot discover unlinked knowledge or
    prove semantic equivalence, absence of duplication, or source approval.
    """
    changed = task_change.get("changed_files", []) if task_change.get("supported") else []
    entry = convergence.get("knowledge_retention", {}) if isinstance(convergence, dict) else {}
    declared = [p for key in ("updated", "created")
                for p in (entry.get(key, []) if isinstance(entry.get(key), list) else [])
                if isinstance(p, str)] if isinstance(entry, dict) else []
    outputs = sorted({p for p in [*changed, *declared]
                      if isinstance(p, str) and p.endswith(".md")
                      and (_safe_path(p))
                      and (p in declared or p.startswith(DURABLE_HOMES))})
    base = {
        "status": "review-required" if outputs else "skipped-no-knowledge-output",
        "sources": [], "possible_overlaps": [], "unread_sources": [],
        "unresolved_references": [], "truncated": False,
        "files_read": 0, "bytes_read": 0, "comparisons": 0,
        "source_attempts": 0, "omitted_source_occurrences": 0,
        "unread_diagnostics_suppressed": 0, "reference_diagnostics_suppressed": 0,
        "repository_scan": False, "retrieval_invoked": False,
        "semantic_verification": False, "absence_of_duplicates_verified": False,
        "limitations": [
            "Only task outputs, prepared sources and explicit local links are considered; unlinked sources were not recalled.",
            "Machine reads do not establish Agent review, approval, equivalent scope, or semantic completeness.",
            "Link anchors, remote references and host imports are not verified by this candidate helper.",
            "Hints require source review; never merge, delete, or confirm knowledge automatically.",
            "Scope fields are bounded contextual excerpts, not complete applicability or authority determinations.",
        ],
    }
    if not outputs:
        return base
    if (not isinstance(entry, dict) or any(
            key in entry and not isinstance(entry[key], list) for key in ("updated", "created"))):
        base["limitations"].append("Malformed knowledge-retention fields were ignored; the protocol validator must review them.")

    prepared = {
        item["path"]: item for item in context.get("artifacts", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    source_digests = {p: item.get("sha256") for p, item in prepared.items()}
    queue = []
    scheduled = set()

    def unread(path, reason):
        if len(base["unread_sources"]) < MAX_FILES:
            base["unread_sources"].append({"path": path, "reason": reason})
        else:
            base["unread_diagnostics_suppressed"] += 1

    def enqueue(path, reason):
        if path in scheduled:
            return
        if len(scheduled) >= MAX_FILES:
            base["truncated"] = True
            base["omitted_source_occurrences"] += 1
            unread(path, "source count budget; not attempted")
            return
        scheduled.add(path)
        queue.append((path, reason))

    def unresolved(path, reference):
        if len(base["unresolved_references"]) < MAX_FILES:
            base["unresolved_references"].append({"source": path, "reference": reference[:256]})
        else:
            base["truncated"] = True
            base["reference_diagnostics_suppressed"] += 1

    for p in outputs:
        enqueue(p, "task-knowledge-output")
    for p in sorted(prepared):
        if p.endswith(".md"):
            enqueue(p, "prepared-context")
    route = context.get("scope_route")
    if isinstance(route, dict):
        for item in route.get("domains", []):
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                enqueue(item["path"], "related-domain")
        for item in route.get("candidates", []) if isinstance(route.get("candidates"), list) else []:
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                enqueue(item["path"], "prepared-route-candidate")
                source_digests.setdefault(item["path"], item.get("sha256"))
    budget = context.get("context_budget")
    counts = ({key: budget.get(key) for key in ("dropped_candidates", "authority_candidates_dropped")}
              if isinstance(budget, dict) else {})
    if isinstance(route, dict):
        counts["route_truncated_candidates"] = route.get("truncated_candidates")
    omitted = {key: value for key, value in counts.items() if type(value) is int and value > 0}
    if omitted:
        base["truncated"] = True
        base["prepared_retrieval_omissions"] = omitted
        base["limitations"].append("Prepared Context omitted candidate sources; this local review does not recover that unmaterialized set.")
    seen = set()
    documents = []
    root = root.resolve()
    while queue:
        path, reason = queue.pop(0)
        if path in seen:
            continue
        seen.add(path)
        base["source_attempts"] += 1
        try:
            if not _safe_path(path):
                raise ValueError("unsafe repository path")
            target = root / path
            if (not target.resolve().is_relative_to(root)
                    or any((root.joinpath(*target.relative_to(root).parts[:i])).is_symlink()
                           for i in range(1, len(target.relative_to(root).parts) + 1))):
                raise ValueError("symlink or escaping source")
            file_stat = target.stat()
            if not stat.S_ISREG(file_stat.st_mode):
                raise ValueError("source is not a regular file")
            size = file_stat.st_size
            if size > MAX_FILE_BYTES or base["bytes_read"] + size > MAX_TOTAL_BYTES:
                base["truncated"] = True
                raise ValueError("source exceeds read budget")
            with target.open("rb") as handle:
                raw = handle.read(MAX_FILE_BYTES + 1)
            if len(raw) > MAX_FILE_BYTES or base["bytes_read"] + len(raw) > MAX_TOTAL_BYTES:
                base["truncated"] = True
                raise ValueError("source exceeds read budget")
            base["files_read"] += 1
            base["bytes_read"] += len(raw)
            decoded = raw.decode("utf-8")
            if decoded.startswith("---\n") and "pact:" in decoded.split("---", 2)[1]:
                raise ValueError("unsupported YAML PACT metadata; source not treated as an ordinary document")
            data, body, _ = parse_markdown_metadata(decoded)
            pact = data.get("pact", {})
            if not isinstance(pact, dict):
                raise ValueError("malformed PACT metadata table")
            if "pact" in data and not isinstance(pact.get("type"), str):
                raise ValueError("PACT metadata missing artifact type")
            if "pact" in data and pact["type"] not in {
                    "domain", "rule", "decision", "change", "drift", "architecture"}:
                raise ValueError("unknown PACT artifact type")
            if any(value is not None and not isinstance(value, str)
                   for value in (pact.get("id"), pact.get("status"))):
                raise ValueError("malformed PACT ID/status metadata")
            if "domains" in pact and (not isinstance(pact["domains"], list)
                                       or any(not isinstance(d, str) for d in pact["domains"])):
                raise ValueError("malformed PACT domain metadata")
            title = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
            item = {
                "path": path, "id": pact.get("id"),
                "artifact_type": pact.get("type", "document"),
                "status": pact.get("status"),
                "title": title.group(1).strip() if title else target.stem,
                "domains": pact.get("domains", []) if isinstance(pact.get("domains", []), list) else [],
                "text": body,
            }
            documents.append(item)
            digest = hashlib.sha256(raw).hexdigest()
            original_sha = source_digests.get(path)
            base["sources"].append({
                **{key: item[key] for key in ("path", "id", "artifact_type", "status", "title", "domains")},
                "scope": _scope(body), "reason": reason,
                "sha256": digest,
                "prepared_source_changed": bool(original_sha and original_sha != digest),
                "agent_read_verified": False,
                "confirmation_inferred": False,
            })
            # One hop from the declared sources or related Domain; no recursive
            # crawl through arbitrary linked implementation/history documents.
            if reason != "explicit-local-link":
                for raw_link in LINK.findall(body):
                    link = raw_link.strip()
                    destination = re.fullmatch(
                        r'''(<[^>]+>|[^\s<>]+)(?:\s+(?:"[^"]*"|'[^']*'))?''', link,
                    )
                    if destination is None:
                        unresolved(path, raw_link)
                        continue
                    link = destination.group(1)
                    if link.startswith("<"):
                        link = link[1:-1]
                    parsed = urlsplit(link)
                    if parsed.scheme or parsed.netloc or link.startswith("#"):
                        continue
                    link_path = unquote(parsed.path)
                    linked = posixpath.normpath(posixpath.join(posixpath.dirname(path), link_path))
                    if linked.endswith(".md") and _safe_path(linked):
                        enqueue(linked, "explicit-local-link")
                    else:
                        unresolved(path, raw_link)
            if original_sha and original_sha != digest:
                base["limitations"].append(
                    f"Prepared source changed: {path}; this hint does not authorize an aligned Convergence disposition.")
        except (OSError, ValueError, UnicodeError, RuntimeError) as exc:
            unread(path, str(exc)[:200])

    # Current task output versus its bounded source inventory. Independent
    # branch outputs are both task deltas after integration, even with distinct IDs.
    for left, right in itertools.combinations(documents, 2):
        if left["path"] not in outputs and right["path"] not in outputs:
            continue
        if base["comparisons"] >= MAX_PAIRS:
            base["truncated"] = True
            break
        base["comparisons"] += 1
        signal = overlap_signal(left, right)
        if signal:
            if len(base["possible_overlaps"]) >= MAX_HINTS:
                base["truncated"] = True
                continue
            base["possible_overlaps"].append({
                "paths": [left["path"], right["path"]],
                "ids": [left["id"], right["id"]],
                "statuses": [left["status"], right["status"]],
                "scopes": [_scope(left["text"]), _scope(right["text"])],
                "signal": signal,
                "reason": "Review possible reuse, duplication or differing scope; no semantic verdict.",
            })

    if isinstance(entry, dict) and entry and entry.get("disposition") != "pending":
        errors, summary = review_retention(
            {"knowledge_retention": entry},
            prepared_paths=[p for p, d in prepared.items() if isinstance(d.get("sha256"), str)],
            prepared_file_states=baseline.get("dirty_files") if baseline.get("kind") == "git" else None,
        )
        base["file_operation_review"] = {"errors": errors, **summary}
    return base
