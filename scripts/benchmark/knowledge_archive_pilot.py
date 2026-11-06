#!/usr/bin/env python3
"""A fixed, local-source documentation rehearsal, never a migration executor.

Only an independent clone is modified. No commits, credentials, project apps,
network services or host configuration are used. The retained output directory
is deliberately create-only so interrupted runs are never replayed or erased.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "pact"))

from check import validate_links
from convergence_coverage import review as review_coverage
from drift_closure import check_closure
from knowledge_retention import review as review_retention
from knowledge_reuse import review as review_reuse
from map import parse_document


PINNED_REVISION = "d7f6bdf014ac67b99666f322f872e3b16524da8c"
SOURCE_REL = "docs/01-业务说明书/03-考制与填报形态标准模型/考制模型-3+3综合改革体系.md"
TARGET_REL = "docs/product/specs/考制模型-3+3综合改革体系.md"
DEFERRED_REL = "docs/01-业务说明书/02-招考通用引擎与基准流程/志愿方案管理、预览与导出规范.md"
FORMAL_REL = "docs/product/rules/result-semantics.md"
CANDIDATE_REL = "docs/product/rules/candidates/reference-recommendation.md"
DOMAIN_REL = "docs/product/domains/profile-batch.md"
CHANGE_REL = "docs/changes/active/2026-11-06-knowledge-archive-pilot.md"
INBOUND = (
    "docs/01-业务说明书/README.md",
    "docs/01-业务说明书/03-考制与填报形态标准模型/README.md",
    "docs/01-业务说明书/04-省级差异与落地矩阵/上海.md",
    "docs/01-业务说明书/04-省级差异与落地矩阵/北京.md",
    "docs/01-业务说明书/04-省级差异与落地矩阵/浙江.md",
    "docs/01-业务说明书/04-省级差异与落地矩阵/海南.md",
)
LINK = re.compile(r"(\[[^\]]+\]\()([^\s)]+)(\))")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class Meter:
    """Explicit Python reads and subprocesses only, not hidden OS/cache I/O."""

    def __init__(self):
        self.calls: list[dict] = []
        self.files_read = 0
        self.bytes_read = 0

    def run(self, argv: list[str], *, cwd: pathlib.Path | None = None,
            allow_failure: bool = False) -> subprocess.CompletedProcess:
        started = time.monotonic()
        result = subprocess.run(
            argv, cwd=cwd, capture_output=True,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0", "PYTHONDONTWRITEBYTECODE": "1"},
            timeout=180, check=False,
        )
        self.calls.append({
            "command": pathlib.Path(argv[0]).name,
            "operation": argv[1] if len(argv) > 1 else "",
            "returncode": result.returncode,
            "seconds": round(time.monotonic() - started, 4),
        })
        if result.returncode and not allow_failure:
            raise RuntimeError(f"{argv[0:2]} failed: {result.stderr.decode(errors='replace')[:1000]}")
        return result

    def read(self, path: pathlib.Path) -> bytes:
        raw = path.read_bytes()
        self.files_read += 1
        self.bytes_read += len(raw)
        return raw


def git(meter: Meter, root: pathlib.Path, *args: str) -> bytes:
    return meter.run(["git", "--no-optional-locks", "-C", str(root), *args]).stdout


def source_state(meter: Meter, root: pathlib.Path) -> dict:
    """Read-only comparison; never refresh the source index or copy secrets."""
    return {
        "head": git(meter, root, "rev-parse", "HEAD").decode().strip(),
        "status_sha256": digest(git(meter, root, "status", "--porcelain=v1", "-z")),
        "tracked_diff_sha256": digest(git(meter, root, "diff", "--binary", "HEAD", "--")),
        "scope_sha256": {p: digest(meter.read(root / p)) for p in (
            SOURCE_REL, DEFERRED_REL, FORMAL_REL, CANDIDATE_REL,
        )},
    }


def rebase_links(text: str, root: pathlib.Path) -> tuple[str, list[dict]]:
    """This one frozen input uses ordinary inline links; reject other forms."""
    mapping = []

    def replace(match: re.Match) -> str:
        raw = match[2]
        parsed = urlsplit(raw)
        if parsed.scheme or parsed.netloc or raw.startswith("#"):
            return match[0]
        old_target = (root / SOURCE_REL).parent / unquote(parsed.path)
        old_target = old_target.resolve()
        if not old_target.is_relative_to(root) or not old_target.is_file():
            raise ValueError("Frozen source has an unsafe/missing inline link")
        replacement = os.path.relpath(old_target, (root / TARGET_REL).parent)
        if parsed.fragment:
            replacement += "#" + parsed.fragment
        mapping.append({"old": raw, "new": replacement, "fragment": parsed.fragment or None})
        return match[1] + replacement + match[3]

    rebased = LINK.sub(replace, text)
    if rebased.count("](") != len(mapping) + text.count("](#"):
        raise ValueError("Frozen source link syntax changed; manual review required")
    return rebased, mapping


def without_destinations(text: str) -> str:
    return LINK.sub(lambda match: match[1] + "SOURCE" + match[3], text)


def incoming_link_updates(root: pathlib.Path, meter: Meter) -> tuple[dict[str, str], list[dict]]:
    """The reviewed fixed input has six ordinary inbound references, no fragments."""
    paths = [p for p in git(meter, root, "grep", "-l", "-z", "-F",
                            pathlib.Path(SOURCE_REL).name, "--").decode().split("\0") if p]
    if set(paths) != set(INBOUND):
        raise ValueError("Incoming source references differ from the six reviewed files; inspect before migration")
    edits: dict[str, str] = {}
    mapping = []
    for path in INBOUND:
        original = meter.read(root / path).decode()
        matches = []

        def replace(match: re.Match) -> str:
            raw = match[2]
            parsed = urlsplit(raw)
            if parsed.scheme or parsed.netloc:
                return match[0]
            destination = ((root / path).parent / unquote(parsed.path)).resolve()
            if destination != root / SOURCE_REL:
                return match[0]
            if parsed.fragment:
                raise ValueError("Frozen inbound fragment changed; manual rendering review required")
            new = os.path.relpath(root / TARGET_REL, (root / path).parent)
            matches.append({"source": path, "old": raw, "new": new})
            return match[1] + new + match[3]

        updated = LINK.sub(replace, original)
        if len(matches) != 1 or without_destinations(updated) != without_destinations(original):
            raise ValueError("Incoming link requires a fresh explicit mapping review")
        edits[path] = updated
        mapping.extend(matches)
    return edits, mapping


def project_markdown_snapshot(target: pathlib.Path) -> dict[str, str]:
    # Use repository-relative parts: this rehearsal itself lives below the
    # parent PACT checkout's .pact/tmp, which must not empty the corpus.
    paths = [p for p in target.rglob("*.md") if p.is_file()
             and not ({".git", ".pact"} & set(p.relative_to(target).parts))]
    return {p.relative_to(target).as_posix(): digest(p.read_bytes()) for p in paths}


def retention(disposition="none", *, updated=(), created=()) -> dict:
    return {"knowledge_retention": {
        "disposition": disposition,
        "rationale": f"Isolated rehearsal: reuse {TARGET_REL}; no product confirmation is inferred.",
        "updated": list(updated), "created": list(created),
    }}


def question_probes(root: pathlib.Path, *, migrated: bool) -> list[dict]:
    """Frozen author-labelled string probes, not independent semantic tests."""
    probes = (
        ("first-choice-optional", SOURCE_REL, "首选科目留空是合法状态", "document", None),
        ("comprehensive-class", SOURCE_REL, "不人为拆成物理类、历史类、文科或理科", "document", None),
        ("province-exception", SOURCE_REL, "浙江的技术科目差异", "document", None),
        ("source-parser-limits", SOURCE_REL, "不能由候选匹配通过推断来源原文已完整校验", "document", None),
        ("batch-form-independent", SOURCE_REL, "切换批次时使用该批次实际填法", "document", None),
        ("historical-basis", SOURCE_REL, "319115188", "document", None),
        ("result-semantics-formal", FORMAL_REL, "不能将错误吞成成功或空数据", "rule", "confirmed"),
        ("reference-still-candidate", CANDIDATE_REL, "不复制进本候选", "rule", "candidate"),
        ("historical-not-current", DEFERRED_REL, "以上“未实施／未验”是分批历史", "document", None),
    )
    results = []
    for ident, original, needle, typ, status in probes:
        path = TARGET_REL if migrated and original == SOURCE_REL else original
        doc = parse_document(root / path, root)
        results.append({
            "question": ident, "source": original, "current_path": path,
            "expected_type": typ, "expected_status": status,
            "found": needle in doc["text"],
            "status_preserved": doc["artifact_type"] == typ and doc["status"] == status,
            "expected_scope": (
                "3+3 ordinary-class provincial policy; batch/data acceptance separate"
                if original == SOURCE_REL else "existing source's declared applicability"
            ),
            "oracle": "author-labelled exact source text, not independent Owner judgment",
        })
    if not all(r["found"] and r["status_preserved"] for r in results):
        raise ValueError("A frozen source-backed question/status probe failed")
    return results


def fixture_rehearsal(folder: pathlib.Path, *, branch_base: pathlib.Path | None = None,
                      meter: Meter | None = None) -> dict:
    """Integration-tree and stale-context checks use synthetic policy only."""
    folder.mkdir()
    paths = ("docs/product/rules/branch-a.md", "docs/product/rules/branch-b.md",
             "docs/product/rules/next-year.md")
    titles = ("Student export permission", "Permission for student exports", "Student export permission")
    scopes = ("2026 ordinary plans; student owner", "2026 ordinary plans; student owner",
              "2027 ordinary plans; planner")
    bodies = (
        "Export requires authorization from the student owner. Permission must be checked before writing the saved plan, while preview access and archive access are separately reviewed.",
        "Before writing the saved plan, check permission from the student owner. Export authorization is required; archive access and preview access are reviewed separately.",
        "Planner access in 2027 follows a distinct synthetic fixture scope and must remain separate even if a title looks identical.",
    )
    for index, path in enumerate(paths):
        target = folder / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f'+++\n[pact]\ntype = "rule"\nid = "RULE-PILOT-{index + 1}"\n'
            'status = "candidate"\n+++\n\n'
            f"# {titles[index]}\n\n## Scope\n\n{scopes[index]}\n\n## Requirement\n\n{bodies[index]}\n",
            encoding="utf-8",
        )
    branch_sources = []
    if branch_base is not None:
        if meter is None:
            raise ValueError("Branch rehearsal requires an explicit command meter")
        for suffix, selected in (("a", paths[:1]), ("b", paths[1:])):
            branch = f"pact-knowledge-pilot-{suffix}"
            worktree = folder.parent / f"independent-branch-{suffix}"
            # These worktrees belong to the independent clone, never the source.
            meter.run(["git", "-C", str(branch_base), "worktree", "add", "-b", branch,
                       str(worktree), "HEAD"])
            emitted = []
            for path in selected:
                candidate = worktree / path
                if candidate.exists():
                    raise ValueError("Synthetic branch output would overwrite an existing source")
                data = (folder / path).read_bytes()
                candidate.parent.mkdir(parents=True, exist_ok=True)
                candidate.write_bytes(data)
                # Integrate only the explicit branch output, without commits.
                (folder / path).write_bytes(candidate.read_bytes())
                emitted.append({"path": path, "sha256": digest(data)})
            branch_sources.append({"branch": branch, "worktree": worktree.name,
                                   "base": git(meter, worktree, "rev-parse", "HEAD").decode().strip(),
                                   "outputs": emitted, "committed": False})
    before = {p: digest((folder / p).read_bytes()) for p in paths}
    merged = review_reuse(folder, {"artifacts": []}, None,
                          {"supported": True, "changed_files": list(paths)}, {})
    pairs = {frozenset(h["paths"]) for h in merged["possible_overlaps"]}
    if frozenset(paths[:2]) not in pairs or frozenset((paths[0], paths[2])) not in pairs:
        raise ValueError("Integrated distinct-ID/scoped candidates were not surfaced")
    if before != {p: digest((folder / p).read_bytes()) for p in paths}:
        raise ValueError("Reuse hint unexpectedly mutated candidate sources")

    context_file = folder / "context.json"
    context = {"artifacts": [{"path": paths[0], "sha256": before[paths[0]],
                               "id": "RULE-PILOT-1", "artifact_type": "rule"}]}
    context_file.write_text(json.dumps(context), encoding="utf-8")
    convergence = {
        "context_sha256": digest(context_file.read_bytes()),
        "coverage": [{"path": paths[0], "disposition": "aligned",
                      "rationale": "Deliberately stale assertion in a negative fixture."}],
    }
    target = folder / paths[0]
    target.write_text(target.read_text() + "\nChanged source scope requires review.\n", encoding="utf-8")
    errors, _ = review_coverage(context, convergence, root=folder, context_path=context_file)
    if not any("changed since Task preparation" in error for error in errors):
        raise ValueError("Stale aligned assertion was not rejected")
    return {
        "kind": ("synthetic candidate policies emitted in independent Git branch worktrees, manually integrated by explicit path; no commits"
                 if branch_sources else "synthetic final-tree fixture; no commits"),
        "branch_sources": branch_sources,
        "integrated_distinct_id_paraphrase_hint": True,
        "same_title_different_scope_hint_without_merge": True,
        "all_candidate_statuses_preserved": all(s["status"] == "candidate" for s in merged["sources"]),
        "advisory_only": not merged["semantic_verification"],
        "source_bytes_unchanged_by_reuse": True,
        "stale_aligned_rejected": True,
        "candidate_assistance": merged,
    }


def manual_procedure_fixture(folder: pathlib.Path, branch_base: pathlib.Path, meter: Meter) -> dict:
    """Fixed manual decisions, not an automatic migration/recovery protocol."""
    folder.mkdir()
    sources = {
        "legacy/source-a.md": "# Synthetic source A\n\nStable background.\n\n## Unresolved retention\n30 or 60 days is undecided.\n",
        "legacy/source-b.md": "# Synthetic source B\n\nThe same toy retention dispute remains open.\n",
        "legacy/unversioned.md": "# Synthetic unsaved source\n\nNo retrievable Git source version exists.\n",
    }
    for path, text in sources.items():
        target = folder / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    drift_path = "docs/drift/known/retention.md"
    drift = folder / drift_path
    drift.parent.mkdir(parents=True)
    drift.write_text(
        '+++\n[pact]\ntype = "drift"\nid = "DRIFT-PILOT-RETENTION"\nstatus = "known"\n+++\n\n'
        '# Synthetic shared retention dispute\n\n'
        '## Conflict sources\n\n[A](../../../legacy/source-a.md) and [B](../../../legacy/source-b.md) '
        'disagree about one toy retention period. [Plan A](../../changes/active/plan-a.md) and '
        '[Plan B](../../changes/active/plan-b.md) reuse this record.\n\n'
        '## Scope\n\nSynthetic 2026 student plan retention; not real project policy.\n\n'
        '## Decision basis\n\nNo real Owner decision was requested or fabricated.\n\n'
        '## Current authority\n\nUndecided. Both source files are held whole pending authority selection.\n\n'
        '## Implementation and verification\n\nNo business implementation is claimed.\n\n'
        '## Remaining issues\n\nOne decision is needed for the shared period; other independent documents may proceed.\n',
        encoding="utf-8",
    )
    for name in ("plan-a", "plan-b"):
        target = folder / f"docs/changes/active/{name}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"# Synthetic {name}\n\nReuse [one dispute](../../drift/known/retention.md).\n", encoding="utf-8")
    # The whole source is retained, including its conflict-free first chapter.
    held_unchanged = all((folder / p).read_text() == text for p, text in sources.items())
    open_check = check_closure(folder, [drift_path])
    if open_check["status"] != "fail" or not held_unchanged:
        raise ValueError("Synthetic held/open dispute was accidentally closed or rewritten")
    missing = meter.run(["git", "-C", str(branch_base), "cat-file", "-e",
                         "HEAD:legacy/unversioned.md"], allow_failure=True)
    if missing.returncode == 0:
        raise ValueError("Unversioned negative fixture unexpectedly has Git provenance")
    # Deliberately perform no retirement when provenance is absent.
    if not (folder / "legacy/unversioned.md").is_file():
        raise ValueError("Unversioned source was retired without a recoverable revision")
    return {
        "kind": "authored manual-procedure rehearsal on synthetic conflict inputs",
        "source_files_held_whole": ["legacy/source-a.md", "legacy/source-b.md"],
        "source_bytes_unchanged": held_unchanged,
        "shared_disputes": 1, "associated_sources": 2, "associated_plans": 2,
        "drift": drift_path, "drift_id": "DRIFT-PILOT-RETENTION", "state": "known",
        "closure_rejected": True, "real_owner_decision": False,
        "independent_real_migration_continued": {"source": SOURCE_REL, "target": TARGET_REL},
        "unversioned_retirement_deferred": True,
        "scope_limits": "Demonstrates the documented manual choices, not semantic conflict detection, consent authenticity or an automated migration engine.",
    }


def run(source: pathlib.Path, output: pathlib.Path, revision: str,
        project_python: str | None, *, upgrade: bool) -> dict:
    # mkdir without exist_ok is intentional: interrupted output is never reused.
    output.mkdir(parents=True)
    meter = Meter()
    report = {
        "stage": "starting", "complete": False, "source_revision": revision,
        "source_root": str(source), "output_root": str(output),
        "source_content_published": False, "project_behavior_verified": False,
        "independent_owner_semantic_review": False, "task_finish_claimed": False,
    }
    started = time.monotonic()
    original_state = None
    try:
        original_state = source_state(meter, source)
        if original_state["head"] != revision:
            raise ValueError("Source HEAD differs from pinned revision; review before selecting a new input")
        report["source_before"] = original_state
        report["stage"] = "independent clone"
        target = output / "checkout"
        # file:// uses Git transport; --no-hardlinks and no shared alternates.
        meter.run(["git", "clone", "--no-hardlinks", "--depth", "1", "--no-checkout",
                   source.as_uri(), str(target)])
        meter.run(["git", "-C", str(target), "checkout", "--detach", revision])
        if (target / ".git/objects/info/alternates").exists():
            raise ValueError("Isolated clone unexpectedly depends on source object storage")
        report["source_dirty_content_copied"] = False
        if project_python:
            baseline_guard = meter.run([project_python, str(target / ".pact/check_project.py"),
                                        "--root", str(target)], cwd=target, allow_failure=True)
            report["project_knowledge_guard_baseline"] = {
                "returncode": baseline_guard.returncode,
                "stdout": baseline_guard.stdout.decode(errors="replace")[:2000],
                "stderr": baseline_guard.stderr.decode(errors="replace")[:2000],
            }
        cold_started = time.monotonic()
        cold_discovery = meter.run([sys.executable, str(target / "pact.py"), "discover",
                                    "考制模型 3+3 综合改革体系", "--limit", "12", "--json"], cwd=target)
        cold_payload = json.loads(cold_discovery.stdout)
        report["cold_knowledge_discovery"] = {
            "seconds": round(time.monotonic() - cold_started, 4),
            "subprocess_calls": 1, "code_scan_requested": False,
            "retrieved_source": SOURCE_REL in {r["path"] for r in cold_payload["results"]},
            "results": [{k: r.get(k) for k in ("path", "artifact_type", "status")} for r in cold_payload["results"]],
        }
        if not report["cold_knowledge_discovery"]["retrieved_source"]:
            raise ValueError("Cold discovery failed to recall the frozen source")
        report["source_history"] = {}
        for path in (SOURCE_REL, DEFERRED_REL, FORMAL_REL, CANDIDATE_REL):
            raw = git(meter, target, "show", f"{revision}:{path}")
            if raw != meter.read(target / path):
                raise ValueError("Source working bytes do not match pinned Git bytes")
            report["source_history"][path] = {"revision": revision, "sha256": digest(raw)}
        report["before_questions"] = question_probes(target, migrated=False)
        inbound_edits, inbound_mapping = incoming_link_updates(target, meter)
        original = meter.read(target / SOURCE_REL).decode()
        kept = {p: meter.read(target / p) for p in (DEFERRED_REL, FORMAL_REL, CANDIDATE_REL)}
        before_doc = parse_document(target / SOURCE_REL, target)

        report["stage"] = "A independent document migration"
        rebased, mapping = rebase_links(original, target)
        if without_destinations(rebased) != without_destinations(original):
            raise ValueError("Source prose changed beyond explicit link mapping")
        new = target / TARGET_REL
        new.parent.mkdir(parents=True, exist_ok=True)
        if new.exists():
            raise ValueError("Pilot target already exists; manual review required")
        new.write_text(rebased, encoding="utf-8")
        for path, text in inbound_edits.items():
            if path != "docs/01-业务说明书/README.md":
                (target / path).write_text(text, encoding="utf-8")
        after_doc = parse_document(new, target)
        if after_doc["artifact_type"] != "document" or after_doc["status"] is not None:
            raise ValueError("Code-derived explanation was elevated to confirmed authority")
        if validate_links(target, [new]):
            raise ValueError("Rebased document has a broken local file target")
        anchors = []
        # Explicit anchor review against the actual target text. This source's
        # only fragment points to a literal HTML alias, not a guessed slug.
        for item in mapping:
            if item["fragment"]:
                file_part, fragment = item["new"].split("#", 1)
                destination = (new.parent / file_part).resolve()
                text = meter.read(destination).decode()
                exists = f'id="{unquote(fragment)}"' in text or f"id='{unquote(fragment)}'" in text
                anchors.append({"reference": item["new"], "explicit_anchor_found": exists})
                if not exists:
                    raise ValueError("Frozen fragment needs a new manual rendering review")
        # Retire only after pinned Git bytes and complete prose transfer exist.
        redirect = os.path.relpath(new, (target / SOURCE_REL).parent)
        (target / SOURCE_REL).write_text(
            "# 已迁移：考制模型 · 3+3 综合改革体系\n\n"
            f"本次隔离试点的现行说明见[唯一正文]({redirect})。本页只保留已有入口，不包含业务正文或稳定 ID。\n",
            encoding="utf-8",
        )
        domain = target / DOMAIN_REL
        domain.write_text(domain.read_text() +
                          "\n## 隔离迁移试点\n\n"
                          f"[3+3 选科与综合科类说明](../specs/{new.name})保持代码派生身份；路由不确认业务要求。\n",
                          encoding="utf-8")
        change = target / CHANGE_REL
        change.parent.mkdir(parents=True, exist_ok=True)
        change.write_text(
            '+++\n[pact]\ntype = "change"\nstatus = "active"\n+++\n\n'
            "# 统一知识归档隔离试点\n\n"
            "## 范围与来源\n\n"
            f"仅迁移 `{SOURCE_REL}`，固定来源 `{revision}:{SOURCE_REL}`，"
            f"SHA256 `{digest(original.encode())}`。新正文见[3+3说明](../../product/specs/{new.name})，"
            "仅修正相对引用，保留正文、条件、例外、来源与现状身份。旧路径为无稳定ID的短跳转。\n\n"
            "## 暂缓与排除\n\n"
            f"`{DEFERRED_REL}` 整份保持原字节；其中历史分批状态与当前验收混合，本轮未审阅完整切换条件，"
            "不把历史未实施当作当前未实施或新发现的业务权威冲突。正式与候选Rule、其他活计划、资料及实现排除。"
            "没有新建业务Drift或替代现有技术债登记；合成冲突演练另存本地测试证据。\n\n"
            "## 后续复用\n\n"
            "B计划读取同一正文，知识保留为none并引用已有来源；不创建第二份说明。"
            "六处已审阅入链直接指向新正文；两个根产品／业务入口最后更新。命令结构通过不代表业务已验收或整库已切换。\n\n"
            "## 验证与中断\n\n"
            "固定问题前后对照、原文与状态核对、明确链接映射及一个显式锚点核对；"
            "宿主导入、全库特殊语法和应用行为未验证。无提交，无发布；中断保留现场，不自动恢复。\n",
            encoding="utf-8",
        )
        # Shared entry is deliberately last, after the independent migration.
        (target / "docs/01-业务说明书/README.md").write_text(
            inbound_edits["docs/01-业务说明书/README.md"], encoding="utf-8")
        product_entry = target / "docs/product/README.md"
        product_entry.write_text(product_entry.read_text() +
                                 "\n## 隔离知识归档试点\n\n"
                                 f"本轮只有[3+3说明](specs/{new.name})完成位置切换，保持代码派生身份。"
                                 "其他业务说明仍在原权威位置；不得据此推断全库迁移完成。\n",
                                 encoding="utf-8")
        changed = [SOURCE_REL, TARGET_REL, DOMAIN_REL, CHANGE_REL, "docs/product/README.md", *INBOUND]
        link_errors = validate_links(target, [target / p for p in changed])
        if link_errors:
            raise ValueError("Changed-document local link errors: " + repr(link_errors))
        for path, raw in kept.items():
            if meter.read(target / path) != raw:
                raise ValueError("Deferred or retained authoritative source changed")
        report["migration"] = {
            "migrated": [{"source": SOURCE_REL, "target": TARGET_REL,
                          "source_revision": revision, "prose_and_conditions_preserved": True,
                          "authority_before": before_doc["status"], "authority_after": after_doc["status"]}],
            "deferred": [{"path": DEFERRED_REL, "whole_file_unchanged": True,
                          "reason": "mixed historical/current evidence not reviewed for whole-file cutover; no new authority conflict asserted"}],
            "retained": [FORMAL_REL, CANDIDATE_REL], "link_mapping": mapping,
            "incoming_link_mapping": inbound_mapping,
            "file_targets_checked": len(changed), "explicit_anchors_checked": anchors,
            "all_repository_references_verified": False,
            "host_imports_and_unenumerated_syntax": "unverified",
            "old_path_operation": "updated", "old_redirect_has_stable_id": False,
            "root_entry_updated_last": True, "change": CHANGE_REL,
        }
        report["after_questions"] = question_probes(target, migrated=True)

        report["stage"] = "B reuse and cost checks"
        prepared = {"artifacts": [{"path": TARGET_REL, "artifact_type": "document",
                                    "sha256": digest(new.read_bytes())}]}
        none = retention()
        # A normal none close must not add any Git/retrieval subprocess calls.
        started_none = time.monotonic()
        with patch("subprocess.run", side_effect=AssertionError("none review invoked a subprocess")):
            errors, none_summary = review_retention(none, changed_files=[], require=True)
            no_output = review_reuse(target, prepared, none,
                                     {"supported": True, "changed_files": []}, {})
        if errors or no_output["files_read"] or no_output["retrieval_invoked"]:
            raise ValueError("Ordinary none review gained unrelated maintenance work")
        report["B"] = {
            "existing_body_reused": TARGET_REL, "new_body_files": 0,
            "retention": none_summary, "reuse_assistance": no_output,
            "seconds": round(time.monotonic() - started_none, 6),
            "additional_subprocesses": 0,
        }
        started_assist = time.monotonic()
        review = review_reuse(target,
                              {"artifacts": [{"path": DOMAIN_REL, "artifact_type": "domain",
                                               "sha256": digest(domain.read_bytes())}]},
                              retention("create", created=[TARGET_REL]),
                              {"supported": True, "changed_files": [TARGET_REL]}, {})
        spec_source = next(row for row in review["sources"] if row["path"] == TARGET_REL)
        if spec_source["status"] is not None or spec_source["confirmation_inferred"]:
            raise ValueError("Standard spec source acquired confirmation via assistance")
        report["bounded_candidate_review"] = {
            "seconds": round(time.monotonic() - started_assist, 6), **review,
        }
        report["multiplan_fixture"] = fixture_rehearsal(output / "synthetic-integration",
                                                        branch_base=target, meter=meter)
        report["manual_procedure_fixture"] = manual_procedure_fixture(
            output / "synthetic-held-sources", target, meter)

        report["stage"] = "project document checks"
        check = meter.run([sys.executable, str(ROOT / "pact.py"), "check", "--root", str(target),
                           "--artifact-only"], allow_failure=True)
        report["artifact_check"] = {"returncode": check.returncode,
                                     "stdout": check.stdout.decode(errors="replace")[:2000],
                                     "stderr": check.stderr.decode(errors="replace")[:2000]}
        if check.returncode:
            raise ValueError("Isolated project's PACT artifact check failed")
        if project_python:
            project_check = meter.run([project_python, str(target / ".pact/check_project.py"),
                                       "--root", str(target)], cwd=target, allow_failure=True)
            report["project_knowledge_guard"] = {
                "returncode": project_check.returncode,
                "stdout": project_check.stdout.decode(errors="replace")[:2000],
                "stderr": project_check.stderr.decode(errors="replace")[:2000],
                "new_findings": sorted(set(project_check.stderr.decode(errors="replace").splitlines())
                                       - set(baseline_guard.stderr.decode(errors="replace").splitlines())),
            }
            if report["project_knowledge_guard"]["new_findings"]:
                raise ValueError("Project knowledge guard introduced findings; review the retained output")
        else:
            report["project_knowledge_guard"] = {"status": "unexecuted; project interpreter not supplied"}

        if upgrade:
            report["stage"] = "isolated framework upgrade preservation"
            knowledge_before = project_markdown_snapshot(target)
            if TARGET_REL not in knowledge_before:
                raise ValueError("Upgrade preservation corpus omitted the migrated business body")
            upgrade_result = meter.run([sys.executable, str(ROOT / "pact.py"), "upgrade", "--target",
                                        str(target), "--apply", "--json"], allow_failure=True)
            upgrade_payload = json.loads(upgrade_result.stdout or b"{}")
            if upgrade_result.returncode or not upgrade_payload.get("applied"):
                report["upgrade"] = {"passed": False, "result": upgrade_payload}
                raise ValueError("Isolated upgrade failed; review preserved output")
            same = all((target / p).is_file() and digest((target / p).read_bytes()) == sha
                       for p, sha in knowledge_before.items())
            if not same:
                raise ValueError("Framework upgrade changed project knowledge bytes")
            report["upgrade"] = {"passed": True, "applied": True,
                                  "project_markdown_files_preserved": len(knowledge_before),
                                  "business_body_in_framework_manifest": TARGET_REL in json.loads(
                                      (target / ".pact/install.json").read_text())["files"],
                                  "notices": upgrade_payload.get("notices", [])}
        else:
            report["upgrade"] = {"status": "unexecuted"}
        after_discovery = meter.run([sys.executable, str(target / "pact.py"), "discover",
                                     "考制模型 3+3 综合改革体系", "--limit", "12", "--json"], cwd=target)
        after_payload = json.loads(after_discovery.stdout)
        report["after_knowledge_discovery"] = {
            "retrieved_target": TARGET_REL in {r["path"] for r in after_payload["results"]},
            "results": [{k: r.get(k) for k in ("path", "artifact_type", "status")} for r in after_payload["results"]],
        }
        if not report["after_knowledge_discovery"]["retrieved_target"]:
            raise ValueError("Post-migration discovery failed to recall the target")
        tracked_diff = git(meter, target, "diff", "--binary", "HEAD", "--")
        report["clone_diff_sha256"] = digest(tracked_diff)
        (output / "clone-tracked.patch").write_bytes(tracked_diff)
        untracked_paths = git(meter, target, "ls-files", "--others", "--exclude-standard", "-z")
        untracked_inventory = []
        for raw_path in untracked_paths.split(b"\0"):
            if not raw_path:
                continue
            path = raw_path.decode("utf-8")
            data = meter.read(target / path)
            untracked_inventory.append({"path": path, "sha256": digest(data), "bytes": len(data)})
        if TARGET_REL not in {row["path"] for row in untracked_inventory}:
            raise ValueError("Reviewable delta omitted the untracked canonical body")
        report["reviewable_delta"] = {
            "tracked_patch": "clone-tracked.patch",
            "untracked_inventory": untracked_inventory,
            "untracked_contents": "Retained at the listed paths below checkout/; no commits or staging.",
        }
        git_diff = git(meter, target, "diff", "--stat", "HEAD", "--").decode()
        (output / "clone-diff-stat.txt").write_text(git_diff, encoding="utf-8")
        report["complete"] = True
        report["stage"] = "completed fixed engineering rehearsal"
        return report
    except Exception as exc:
        report["error"] = str(exc)
        raise
    finally:
        if original_state is not None:
            after = source_state(meter, source)
            report["source_after"] = after
            report["original_state_unchanged"] = after == original_state
            if after != original_state:
                report["original_change_attribution"] = (
                    "Source changed during read-only observation; this script has no source mutation commands. "
                    "Concurrent authorship is unknown; do not claim source state stayed identical.")
        report["cost"] = {
            "elapsed_seconds": round(time.monotonic() - started, 4),
            "subprocess_calls": len(meter.calls), "calls": meter.calls,
            "instrumented_explicit_python_reads": meter.files_read,
            "instrumented_explicit_python_read_bytes": meter.bytes_read,
            "measurement_limits": "Counts exclude helper/internal subprocess file I/O and OS cache reads; candidate helper has its own counters.",
        }
        (output / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--revision", default=PINNED_REVISION)
    parser.add_argument("--project-python", help="Approved source-project interpreter, used only for its document guard")
    parser.add_argument("--upgrade", action="store_true", help="Exercise authorized PACT upgrade in the independent clone")
    args = parser.parse_args()
    source, output = args.source.expanduser().resolve(), args.output.expanduser().resolve()
    if output.is_relative_to(source) or source.is_relative_to(output):
        parser.error("Source and output must be disjoint")
    try:
        result = run(source, output, args.revision, args.project_python, upgrade=args.upgrade)
    except Exception as exc:
        print(f"Pilot failed; retained output for review: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"complete": result["complete"], "result": str(output / "result.json"),
                      "original_state_unchanged": result["original_state_unchanged"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
