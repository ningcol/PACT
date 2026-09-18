#!/usr/bin/env python3
"""Conservative, explainable PACT impact analysis."""

from __future__ import annotations

import argparse
import fnmatch
import json
import pathlib
import re
import subprocess
import sys
import tempfile

from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = ROOT / ".pact" / "schema" / "impact-report.schema.json"
STABLE_ID = re.compile(r"\b(?:DOMAIN|RULE|DEC|INV|DRIFT)-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")


def normalize_path(value: str) -> str:
    value = value.replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    return value


def target(doc: dict) -> dict:
    return {
        "path": doc["path"],
        "id": doc.get("id"),
        "artifact_type": doc["artifact_type"],
        "title": doc["title"],
    }


def changed_from_git(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git diff failed")
    return [normalize_path(line) for line in result.stdout.splitlines() if line.strip()]


def build_map() -> dict:
    with tempfile.TemporaryDirectory(prefix="pact-impact-") as tmp:
        output = pathlib.Path(tmp) / "project-map.json"
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "pact" / "map.py"), "--output", str(output)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "map failed")
        return json.loads(output.read_text(encoding="utf-8"))


def read_text(path: str) -> str:
    candidate = ROOT / path
    if not candidate.is_file() or candidate.stat().st_size > 1_000_000:
        return ""
    try:
        return candidate.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def validate(report: dict) -> list[str]:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(report), key=lambda e: list(e.path)):
        loc = ".".join(str(p) for p in err.path)
        errors.append(f"{loc or '<root>'}: {err.message}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze project knowledge impact")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--files", nargs="+", help="explicit changed repository paths")
    source.add_argument("--base", help="git base ref for BASE...HEAD diff")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()

    try:
        changed = (
            [normalize_path(x) for x in args.files]
            if args.files
            else changed_from_git(args.base, args.head)
        )
        changed = sorted(set(changed))
        index = build_map()
    except Exception as exc:
        print(f"PACT impact: setup failed: {exc}", file=sys.stderr)
        return 2

    docs = index.get("documents", [])
    id_to_doc = {doc["id"]: doc for doc in docs if doc.get("id")}

    deterministic: list[dict] = []
    det_keys: set[tuple[str, str, str]] = set()
    mapped_files: set[str] = set()
    impacted_domains: set[str] = set()
    candidate_reasons: dict[str, set[str]] = {}
    candidate_scores: dict[str, int] = {}

    def add_det(source_file: str, relation: str, doc: dict) -> None:
        key = (source_file, relation, doc["path"])
        if key in det_keys:
            return
        det_keys.add(key)
        deterministic.append({
            "source_file": source_file,
            "relation": relation,
            "target": target(doc),
        })
        mapped_files.add(source_file)
        impacted_domains.update(doc.get("domains", []))
        if doc.get("artifact_type") == "domain" and doc.get("id"):
            impacted_domains.add(doc["id"])

    for changed_file in changed:
        text = read_text(changed_file)

        for doc in docs:
            if doc["path"] == changed_file:
                add_det(changed_file, "artifact-changed", doc)

            if doc.get("artifact_type") == "domain":
                for pattern in doc.get("paths", []):
                    if fnmatch.fnmatch(changed_file, pattern):
                        add_det(changed_file, "declared-domain-path", doc)

            normalized_links = {normalize_path(x) for x in doc.get("links", [])}
            if changed_file in normalized_links:
                add_det(changed_file, "explicit-doc-link", doc)

            normalized_verification = {normalize_path(x) for x in doc.get("verification", [])}
            if changed_file in normalized_verification:
                add_det(changed_file, "verification-reference", doc)

        for stable_id in set(STABLE_ID.findall(text)):
            doc = id_to_doc.get(stable_id)
            if doc:
                add_det(changed_file, "explicit-stable-id", doc)

    for doc in docs:
        doc_domains = set(doc.get("domains", []))
        shared = doc_domains & impacted_domains
        if shared and not any(x["target"]["path"] == doc["path"] for x in deterministic):
            candidate_reasons.setdefault(doc["path"], set()).add(
                "shares impacted domain: " + ", ".join(sorted(shared))
            )
            candidate_scores[doc["path"]] = max(candidate_scores.get(doc["path"], 0), 100)

    deterministic_docs = [
        id_to_doc.get(item["target"].get("id"))
        for item in deterministic
        if item["target"].get("id")
    ]
    for doc in [d for d in deterministic_docs if d]:
        for related_id in doc.get("related", []):
            related = id_to_doc.get(related_id)
            if related and not any(x["target"]["path"] == related["path"] for x in deterministic):
                candidate_reasons.setdefault(related["path"], set()).add(
                    f"explicitly related to {doc.get('id') or doc['path']}"
                )
                candidate_scores[related["path"]] = max(candidate_scores.get(related["path"], 0), 90)

    doc_by_path = {doc["path"]: doc for doc in docs}
    candidates = []
    for path, reasons in candidate_reasons.items():
        doc = doc_by_path[path]
        candidates.append({
            "score": candidate_scores[path],
            "reasons": sorted(reasons),
            "target": target(doc),
        })
    candidates.sort(key=lambda x: (-x["score"], x["target"]["path"]))

    report = {
        "version": 1,
        "changed_files": changed,
        "impacted_domains": sorted(impacted_domains),
        "deterministic_impacts": deterministic,
        "candidate_impacts": candidates,
        "unmapped_files": sorted(set(changed) - mapped_files),
    }

    errors = validate(report)
    if errors:
        print("PACT impact: generated invalid report", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = pathlib.Path(args.output)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(f"PACT impact: report -> {output}")
        return 0

    if args.json:
        print(rendered, end="")
        return 0

    print(f"PACT impact: {len(changed)} changed file(s)")
    print(f"Deterministic relationships: {len(deterministic)}")
    print(f"Candidate relationships: {len(candidates)}")
    if impacted_domains:
        print("Impacted domains: " + ", ".join(sorted(impacted_domains)))
    if report["unmapped_files"]:
        print("Unmapped changed files:")
        for path in report["unmapped_files"]:
            print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
