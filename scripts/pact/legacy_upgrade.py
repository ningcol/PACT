"""Strict, opt-in historical PACT data conversion used ONLY by upgrade.

The installed runtime stays TOML-only. Never invent Decision IDs, Owner
approval, task completion or the meaning of retired project configuration.
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import re
import tomllib

from schema_validate import load_schema, validate_instance

SEEDS = (
    (".pact/config.yaml", ".pact/config.toml", "config"),
    (".pact/baseline.yaml", ".pact/baseline.toml", "baseline"),
    (".pact/fitness.yaml", ".pact/fitness.toml", "fitness"),
)
RETIRED_DEFAULTS = {
    "paths": {
        "product_truth": "docs/product", "architecture": "docs/architecture",
        "decisions": ".agents/decisions", "changes": "docs/changes",
        "drift": "docs/drift", "skills": ".agents/skills",
    },
    "risk": {"levels": ["low", "medium", "high"]},
    "discovery": {"use_canonical_vocabulary": True, "derived_cache": ".pact/cache"},
    "convergence": {
        "code_wins_product_truth": False, "deterministic_fact_mismatch": "fail",
        "heuristic_drift": "warn",
    },
}
KNOWLEDGE_DIRS = (
    ".agents/decisions", "docs/product/rules", "docs/product/domains",
    "docs/architecture", "docs/changes", "docs/drift",
)
FRONT = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", re.DOTALL)
KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*\Z")
MAX_SOURCE = 2 * 1024 * 1024


class LegacyUpgradeError(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def scalar(value: str):
    v = value.strip()
    if v in ("[]", "{}"):
        return [] if v == "[]" else {}
    if v.lower() in {"true", "false"}:
        return v.lower() == "true"
    if re.fullmatch(r"-?(?:0|[1-9][0-9]*)", v):
        return int(v)
    if v.startswith('"') and v.endswith('"'):
        try:
            out = json.loads(v)
        except json.JSONDecodeError as exc:
            raise LegacyUpgradeError("ambiguous YAML quoted scalar") from exc
        if isinstance(out, str):
            return out
        raise LegacyUpgradeError("YAML quoted value was not a string")
    if v.startswith("'") and v.endswith("'"):
        return v[1:-1].replace("''", "'")
    if v.startswith("[") and v.endswith("]"):
        try:
            out = ast.literal_eval(v)
        except (ValueError, SyntaxError) as exc:
            raise LegacyUpgradeError("only quoted legacy flow-list items supported") from exc
        if isinstance(out, list) and all(type(x) in (str, int, bool) for x in out):
            return out
        raise LegacyUpgradeError("unsupported YAML flow list")
    if (
        not v or v.casefold() in {"null", "none", "yes", "no", "on", "off"}
        or v == "~"
        or (v.startswith('"') != v.endswith('"'))
        or (v.startswith("'") != v.endswith("'"))
        or ": " in v
        or v.startswith(("{", "[", "!", "&", "*", "|", ">", "%"))
        or re.search(r"\s+#", v) or "\t" in v or "\r" in v
    ):
        raise LegacyUpgradeError("ambiguous YAML scalar; requires manual migration")
    return v


def parse_yaml(text: str) -> dict:
    """Tightly bound subset emitted by historical PACT, never general YAML."""
    if len(text.encode("utf-8")) > 256 * 1024:
        raise LegacyUpgradeError("YAML source exceeds 256 KiB")
    lines = []
    for i, raw in enumerate(text.splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        depth = len(raw) - len(raw.lstrip(" "))
        if depth % 2 or "\t" in raw or raw.strip() in {"---", "..."}:
            raise LegacyUpgradeError(f"unsupported legacy indentation at line {i}")
        lines.append((depth, raw.strip()))
    if not lines or lines[0][0]:
        raise LegacyUpgradeError("legacy YAML is empty or lacks a root")
    result: dict = {}
    stack = [(-1, result)]
    for n, (depth, line) in enumerate(lines):
        while stack and depth <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise LegacyUpgradeError("YAML indentation escapes root")
        parent = stack[-1][1]
        if line.startswith("- "):
            if not isinstance(parent, list):
                raise LegacyUpgradeError("YAML list item has no list parent")
            item = line[2:].strip()
            matched = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*): +(.+)", item)
            if matched:
                value = {matched.group(1): scalar(matched.group(2))}
                parent.append(value)
                stack.append((depth, value))
            else:
                parent.append(scalar(item))
            continue
        matched = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):(?: *(.*))?", line)
        if not matched or not isinstance(parent, dict):
            raise LegacyUpgradeError("unsupported YAML mapping or scalar syntax")
        name, raw = matched.group(1), matched.group(2)
        if name in parent:
            raise LegacyUpgradeError(f"duplicate YAML key: {name}")
        if raw:
            parent[name] = scalar(raw)
        else:
            lookahead = lines[n + 1] if n + 1 < len(lines) else None
            value = [] if lookahead and lookahead[0] > depth and lookahead[1].startswith("- ") else {}
            parent[name] = value
            stack.append((depth, value))
    return result


def toml_value(value) -> str:
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is int:
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(v) for v in value) + "]"
    raise LegacyUpgradeError("legacy setting has an unsupported value type")


def table(name: str, data: dict) -> str:
    if not isinstance(data, dict):
        raise LegacyUpgradeError(f"{name} must be a mapping")
    parts = []
    for key, value in data.items():
        if not KEY.fullmatch(key):
            raise LegacyUpgradeError(f"unsafe TOML mapping key {key!r}")
        parts.append(f"{key} = {toml_value(value)}")
    return f"[{name}]\n" + "\n".join(parts) + "\n"


def seed_bytes(root: pathlib.Path, kind: str, old: bytes) -> bytes:
    try:
        data = parse_yaml(old.decode("utf-8"))
    except UnicodeError as exc:
        raise LegacyUpgradeError("YAML is not UTF-8") from exc
    if data.get("version") != 1 or type(data.get("version")) is not int:
        raise LegacyUpgradeError("historical seed must have version: 1")
    if kind == "config":
        if set(data) - {"version", "owner", *RETIRED_DEFAULTS}:
            raise LegacyUpgradeError("unknown Owner config keys")
        for key, expected in RETIRED_DEFAULTS.items():
            if key in data and data[key] != expected:
                raise LegacyUpgradeError(
                    f"custom legacy {key} cannot be silently dropped; manual Owner review required"
                )
        owner = data.get("owner")
        if not isinstance(owner, dict):
            raise LegacyUpgradeError("legacy Owner Profile absent")
        wanted = {"version": 1, "owner": owner}
        text = "version = 1\n\n" + table("owner", {
            k: v for k, v in owner.items() if k != "communication"
        }) + "\n" + table("owner.communication", owner.get("communication"))
    elif kind == "baseline":
        if set(data) - {"version", "reviews", "notes"}:
            raise LegacyUpgradeError("unknown legacy baseline keys")
        reviews = data.get("reviews")
        if not isinstance(reviews, dict):
            raise LegacyUpgradeError("legacy baseline review record absent")
        reviews = dict(reviews)
        # PACT 0.2 had no Agent bootstrap review. Never assert it completed.
        reviews.setdefault("agent_bootstrap", "pending")
        wanted = {"version": 1, "reviews": reviews, "notes": data.get("notes", {})}
        text = "version = 1\n\n" + table("reviews", wanted["reviews"]) + "\n" + table("notes", wanted["notes"])
    elif kind == "fitness":
        if set(data) - {"version", "checks"}:
            raise LegacyUpgradeError("unknown legacy fitness keys")
        wanted = {"version": 1, "checks": data.get("checks")}
        checks = wanted["checks"]
        if not isinstance(checks, list):
            raise LegacyUpgradeError("invalid legacy fitness check list")
        text = "version = 1\nchecks = []\n" if not checks else "version = 1\n"
        for check in checks:
            text += "\n[[checks]]\n" + "\n".join(
                f"{key} = {toml_value(value)}" for key, value in check.items()
            ) + "\n"
    else:
        raise LegacyUpgradeError("unknown legacy seed type")
    schema = load_schema(root / ".pact" / "schema" / f"{kind}.schema.json")
    errors = validate_instance(wanted, schema)
    if errors:
        raise LegacyUpgradeError("; ".join(errors[:5]))
    if tomllib.loads(text) != wanted:
        raise LegacyUpgradeError("converted TOML does not preserve legacy values")
    return text.encode("utf-8")


def document_bytes(old: bytes) -> bytes:
    if len(old) > MAX_SOURCE:
        raise LegacyUpgradeError("legacy authority document exceeds 2 MiB")
    try:
        raw = old.decode("utf-8")
    except UnicodeError as exc:
        raise LegacyUpgradeError("authority document is not UTF-8") from exc
    match = FRONT.match(raw)
    if not match:
        raise LegacyUpgradeError("old Decision lacks machine-readable YAML metadata")
    values = parse_yaml(match.group(1))
    if set(values) != {"pact"} or not isinstance(values["pact"], dict):
        raise LegacyUpgradeError("unrecognized legacy authority metadata")
    meta = values["pact"]
    kind = meta.get("type")
    if kind not in {"decision", "domain", "rule", "change", "drift", "architecture"}:
        raise LegacyUpgradeError("unknown legacy authority kind")
    if kind == "decision" and (
        not isinstance(meta.get("id"), str)
        or not re.fullmatch(r"DEC-[A-Z0-9-]+", meta["id"])
        or meta.get("status") not in {
            "proposed", "implemented", "rejected", "archived", "superseded"
        }
    ):
        raise LegacyUpgradeError("Decision needs original stable ID and status; cannot invent")
    if kind in {"rule", "domain"} and (
        not isinstance(meta.get("id"), str)
        or not meta["id"].startswith("RULE-" if kind == "rule" else "DOMAIN-")
        or not isinstance(meta.get("status"), str)
    ):
        raise LegacyUpgradeError("Product authority needs original ID and status")
    converted = table("pact", meta)
    if tomllib.loads(converted) != values:
        raise LegacyUpgradeError("metadata did not round-trip unchanged")
    # All authoritative prose after front matter remains the original bytes.
    return ("+++\n" + converted + "+++\n").encode("utf-8") + raw[match.end():].encode("utf-8")


def render(root: pathlib.Path, target: pathlib.Path, op: dict) -> bytes:
    original_path = target / op["legacy_path"]
    if original_path.is_symlink() or not original_path.is_file():
        raise LegacyUpgradeError("legacy source must be a regular file")
    original = original_path.read_bytes()
    if sha(original) != op["legacy_sha256"]:
        raise LegacyUpgradeError("legacy source changed after plan")
    if op["action"] == "migrate-legacy-seed":
        transformed = seed_bytes(root, op["legacy_kind"], original)
    elif op["action"] == "migrate-legacy-metadata":
        transformed = document_bytes(original)
    else:
        raise LegacyUpgradeError("unknown legacy upgrade operation")
    if sha(transformed) != op["source_sha256"]:
        raise LegacyUpgradeError("legacy transformation changed after planning")
    return transformed


def scan(
    root: pathlib.Path, target: pathlib.Path, tracked: dict,
    migrate: bool, *, installed_version: str = "unknown",
) -> dict:
    """Pure plan of source-bound operations and blockers; never edits target."""
    operations, conflicts, notices = [], [], []

    def append(op: dict):
        if migrate:
            operations.append(op)
        else:
            conflicts.append({
                "path": op["legacy_path"],
                "reason": "0.4 no longer interprets legacy YAML; use --migrate-legacy",
            })

    for legacy_rel, new_rel, kind in SEEDS:
        path, new_path = target / legacy_rel, target / new_rel
        if not path.exists() and not path.is_symlink():
            continue
        if new_path.exists() or new_path.is_symlink():
            # The 0.1/0.2 runtime used YAML as Owner truth, even if someone
            # separately created a TOML default. Do not silently switch to
            # the new TOML when its values disagree with the real old source.
            if installed_version.startswith(("0.1.", "0.2.")):
                try:
                    if path.is_symlink() or new_path.is_symlink():
                        raise LegacyUpgradeError("ambiguous symlinked legacy/current seed")
                    converted = seed_bytes(root, kind, path.read_bytes())
                    expected = tomllib.loads(converted.decode("utf-8"))
                    actual = tomllib.loads(new_path.read_text(encoding="utf-8"))
                    if actual != expected:
                        raise LegacyUpgradeError(
                            "old runtime used YAML but current TOML differs; "
                            "manually reconcile the Owner settings and do not "
                            "overwrite either project-owned file"
                        )
                except (OSError, UnicodeError, ValueError, tomllib.TOMLDecodeError) as exc:
                    conflicts.append({
                        "path": legacy_rel,
                        "reason": f"ambiguous historical YAML/TOML settings: {exc}",
                    })
                    continue
            notices.append({
                "kind": "archived-YAML-seed", "path": legacy_rel,
                "reason": f"existing {new_rel} is authoritative; historical YAML is not read by 0.4",
            })
            continue
        try:
            if path.is_symlink():
                raise LegacyUpgradeError("legacy seed symlink cannot be migrated")
            data = path.read_bytes()
            converted = seed_bytes(root, kind, data)
            append({
                "action": "migrate-legacy-seed", "path": new_rel,
                "legacy_path": legacy_rel, "legacy_kind": kind,
                "legacy_sha256": sha(data), "source_sha256": sha(converted),
                "reason": "explicitly convert historical project-owned YAML",
            })
        except (OSError, ValueError) as exc:
            conflicts.append({"path": legacy_rel, "reason": f"manual legacy seed migration required: {exc}"})

    count = 0
    for rel_dir in KNOWLEDGE_DIRS:
        directory = target / rel_dir
        if directory.is_symlink():
            conflicts.append({"path": rel_dir, "reason": "symlinked authority directory"})
            continue
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.md")):
            count += 1
            rel = path.relative_to(target).as_posix()
            if count > 6000:
                conflicts.append({"path": rel_dir, "reason": "authority audit limit exceeded"})
                break
            # READMEs and templates are normally non-authoritative, but a
            # project may have placed real PACT metadata there. Skip only
            # when no PACT authority header is present; unchanged historical
            # framework templates are handled by the source-hash rule below.
            if path.name in {"README.md", "TEMPLATE.md"}:
                try:
                    if not re.search(
                        rb"(?m)^pact:\s*(?:\r?\n|$)",
                        path.read_bytes()[:256 * 1024],
                    ):
                        continue
                except OSError as exc:
                    conflicts.append({
                        "path": rel,
                        "reason": f"cannot inspect historical authority page: {exc}",
                    })
                    continue
            record = tracked.get(rel, {})
            if record.get("management") == "framework":
                # Old full-profile installs managed governance/doc examples.
                # An unchanged example is safe for the normal obsolete-file
                # removal path, but a locally edited copy was effectively
                # adopted by the project. Never silently detach its YAML
                # authority without reviewing the change and original source.
                try:
                    if (
                        path.is_symlink() or not path.is_file()
                        or sha(path.read_bytes()) != record.get("installed_sha256")
                    ):
                        conflicts.append({
                            "path": rel,
                            "reason": (
                                "historically framework-owned knowledge was locally "
                                "modified; review project authority and detach/migrate "
                                "manually before upgrading"
                            ),
                        })
                except OSError as exc:
                    conflicts.append({
                        "path": rel,
                        "reason": f"historically framework-owned source unreadable: {exc}",
                    })
                continue
            try:
                if path.is_symlink() or path.stat().st_size > MAX_SOURCE:
                    raise LegacyUpgradeError("unsafe or oversized authority document")
                old = path.read_bytes()
                # Both LF and CRLF TOML frontmatter are already current; a
                # Windows checkout must not be treated as legacy YAML.
                if old.startswith((b"+++\n", b"+++\r\n")):
                    continue
                needs = rel.startswith(".agents/decisions/") or (
                    old.startswith((b"---\n", b"---\r\n"))
                    and re.search(rb"(?m)^pact:\s*(?:\r?\n|$)", old[:256 * 1024])
                )
                if not needs:
                    continue
                converted = document_bytes(old)
                append({
                    "action": "migrate-legacy-metadata", "path": rel,
                    "legacy_path": rel, "legacy_sha256": sha(old),
                    "source_sha256": sha(converted),
                    "reason": "convert original metadata without changing Owner rationale",
                })
            except (OSError, ValueError) as exc:
                conflicts.append({"path": rel, "reason": f"manual authority review required: {exc}"})

    # The historical AGENTS.md is project-owned and must not be overwritten.
    # It can still refer to deleted YAML sources or pre-compact CLI commands,
    # so report the necessary manual reconciliation without inventing Owner
    # acceptance or replacing the project's Agent instructions.
    if not installed_version.startswith("0.4."):
        guide = target / "AGENTS.md"
        if guide.is_symlink():
            conflicts.append({
                "path": "AGENTS.md",
                "reason": "legacy Agent guide is a symlink and requires manual review",
            })
        elif guide.is_file():
            try:
                raw_guide = guide.read_text(encoding="utf-8")
                if ".pact/baseline.yaml" in raw_guide or ".pact/config.yaml" in raw_guide:
                    notices.append({
                        "kind": "legacy-agent-guide",
                        "path": "AGENTS.md",
                        "reason": (
                            "existing project-owned Agent guide still names old YAML; "
                            "after upgrade review the guide and change references to "
                            "the authoritative TOML/compact PACT commands manually"
                        ),
                    })
            except (OSError, UnicodeError) as exc:
                conflicts.append({
                    "path": "AGENTS.md",
                    "reason": f"historical Agent guide cannot be audited: {exc}",
                })

    tasks = target / ".pact" / "tasks"
    # Only historical prepared tasks have a different trust/provenance format.
    # A current-format 0.4 task must not prevent a routine 0.4 upgrade.
    if not installed_version.startswith("0.4."):
        if tasks.is_symlink():
            conflicts.append({"path": ".pact/tasks", "reason": "symlinked task state"})
        elif tasks.is_dir():
            for task in sorted(tasks.glob("*/task.json")):
                rel = task.relative_to(target).as_posix()
                try:
                    if task.is_symlink() or task.parent.is_symlink():
                        raise LegacyUpgradeError("task state is a symlink")
                    status = json.loads(task.read_text(encoding="utf-8"))
                    if not isinstance(status, dict) or status.get("status") != "completed":
                        conflicts.append({
                            "path": rel, "reason": (
                                "incomplete historical task cannot safely use the new completion "
                                "contract; finish or archive under old runtime first"
                            ),
                        })
                except (OSError, ValueError) as exc:
                    conflicts.append({"path": rel, "reason": f"task state review required: {exc}"})
    return {"operations": operations, "conflicts": conflicts, "notices": notices}
