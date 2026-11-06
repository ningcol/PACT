"""Opt-in, local Drift closure checks; no inventory or semantic authority verdict.

Only the named Drift files, their direct file references, and the artifact schema
are read. ID-only edges must have a direct Markdown locator in this bounded set;
the checker never searches the repository to resolve them.
"""
from __future__ import annotations

import pathlib
import re
from urllib.parse import unquote, urlsplit

from formats import parse_markdown_metadata
from schema_validate import load_schema, validate_instance

SECTIONS = (
    "Conflict sources", "Scope", "Decision basis", "Current authority",
    "Implementation and verification", "Remaining issues",
)
# Keep these headings stable: they are a local closure interface, not a new
# artifact type or a confirmation state for an ordinary business specification.
PLACEHOLDER = re.compile(
    r"<[^>\n]+>|\b(?:TODO|TBD|FIXME|PLACEHOLDER)\b|"
    r"(?:待填写|填写于|填入此处)|"
    r"\[(?:describe|insert|fill)[^\]\n]*\]", re.I,
)
NONE_AUTHORITY = re.compile(
    r"^(?:none|unknown|undecided|not\s+(?:yet\s+)?(?:chosen|selected|decided)|"
    r"no\s+(?:current\s+)?authority|未决定|未选择|无|未知)(?:[.!。\s]|$)", re.I,
)


def _without_code(text: str) -> str:
    """Ignore examples/comments when requiring real sections and locators."""
    text = re.sub(r"<!--[\s\S]*?-->", "", text)
    lines = []
    fence = None
    for line in text.splitlines():
        match = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is None:
            lines.append(line)
    return "\n".join(lines)


def _has_placeholder(text: str) -> bool:
    # Angle-wrapped Markdown destinations are locators, not template fields.
    text = re.sub(r"\]\(<[^>\n]+>(?:\s+[^)\n]*)?\)", "](locator)", text)
    text = re.sub(r"(?m)^(\s{0,3}\[[^\]\n]+\]:\s*)<[^>\n]+>", r"\1locator", text)
    # Accepted records must describe real pending work. A standalone prompt is
    # empty scaffolding; the same words inside concrete factual prose are not.
    return bool(PLACEHOLDER.search(text) or re.fullmatch(
        r"\s*(?:待补充|待确认)[。.!]?\s*", text,
    ))


def _sections(text: str, level: int = 2) -> tuple[dict[str, str], list[str]]:
    parts: dict[str, str] = {}
    duplicates = []
    pattern = re.compile(r"^" + "#" * level + r" (.+?)\s*#*\s*$", re.M)
    headings = list(pattern.finditer(text))
    for index, match in enumerate(headings):
        name = match.group(1).strip()
        if name in parts:
            duplicates.append(name)
        parts[name] = text[match.end():headings[index + 1].start() if index + 1 < len(headings) else len(text)].strip()
    return parts, duplicates


def _links(text: str, reference_context: str | None = None) -> tuple[list[str], bool]:
    """Read common inline/reference Markdown locators without guessing imports.

    Angle destinations, spaces inside angle destinations, nested parentheses and
    optional titles are supported. Unknown bracket/host forms are disclosed.
    """
    links: list[str] = []
    consumed: list[tuple[int, int]] = []
    for match in re.finditer(r"!?\[[^\]\n]*\]\(", text):
        pos, start = match.end(), match.end()
        if pos < len(text) and text[pos] == "<":
            end = text.find(">", pos + 1)
            close = text.find(")", end + 1) if end >= 0 else -1
            if end >= 0 and close >= 0:
                links.append(text[pos + 1:end])
                consumed.append((match.start(), close + 1))
            continue
        depth = 0
        while pos < len(text):
            char = text[pos]
            if char == "\\" and pos + 1 < len(text):
                pos += 2
                continue
            if char == "(":
                depth += 1
            elif char == ")":
                if depth == 0:
                    break
                depth -= 1
            elif char.isspace() and depth == 0:
                break
            pos += 1
        if pos > start:
            close = text.find(")", pos)
            if close >= 0:
                links.append(text[start:pos])
                consumed.append((match.start(), close + 1))
    definitions: dict[str, str] = {}
    definition_pattern = r"^\s{0,3}\[([^\]\n]+)\]:\s*(<[^>\n]+>|\S+).*$"
    for match in re.finditer(definition_pattern, reference_context or text, re.M):
        definitions[match.group(1).strip().casefold()] = match.group(2).strip("<>")
    for match in re.finditer(definition_pattern, text, re.M):
        consumed.append((match.start(), match.end()))
    for match in re.finditer(r"!?\[([^\]\n]*)\]\[([^\]\n]*)\]", text):
        label = (match.group(2) or match.group(1)).strip().casefold()
        if label in definitions:
            links.append(definitions[label])
            consumed.append((match.start(), match.end()))
    # A used shortcut reference is also a valid locator.
    for match in re.finditer(r"(?<!!)\[([^\]\n]+)\]", text):
        if any(start <= match.start() < end for start, end in consumed):
            continue
        label = match.group(1).strip().casefold()
        if label in definitions:
            links.append(definitions[label])
            consumed.append((match.start(), match.end()))
    remainder = list(text)
    for start, end in consumed:
        remainder[start:end] = " " * (end - start)
    rest = "".join(remainder)
    unsupported = bool(re.search(r"\[[^\]\n]+\]|(?<!\w)@[\w./-]+|\b(?:import|include)\s*[:(]", rest))
    return list(dict.fromkeys(links)), unsupported


def _safe_file(root: pathlib.Path, source: pathlib.Path, raw: str) -> pathlib.Path:
    if not raw or "\x00" in raw or "\\" in raw:
        raise ValueError("invalid or unsupported file path")
    path = root / raw.lstrip("/") if raw.startswith("/") else source.parent / raw
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("reference escapes repository root")
    # Resolve ../ legitimately, but never follow symlinks to aliases or escapes.
    relative = pathlib.Path(path.absolute()).relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("symlink reference is not a stable source identity")
    if not path.is_file():
        raise ValueError("reference target is not a file")
    return resolved


def _has_source_locator(text: str, context: str) -> bool:
    for raw in _links(text, context)[0]:
        try:
            parsed = urlsplit(raw)
        except ValueError:
            continue
        if not parsed.scheme or parsed.scheme in {"http", "https", "mailto"}:
            return True
    return False


def check_closure(root: pathlib.Path, requested: list[str]) -> dict:
    root = root.resolve()
    result = {
        "mode": "drift-closure", "status": "pass", "drifts": [], "errors": [],
        "checked_paths": [], "references": [], "unverified": [],
        "verification_boundaries": {
            "scope": "explicit Drift records and direct references only",
            "repository_inventory_scanned": False,
            "global_id_uniqueness_verified": False,
            "owner_confirmation_verified": False,
            "business_semantics_verified": False,
            "implementation_behavior_verified": False,
            "anchors_verified": False,
            "remote_targets_verified": False,
            "host_imports_verified": False,
        },
    }
    errors = result["errors"]
    snapshots: dict[pathlib.Path, bytes] = {}
    file_states: dict[pathlib.Path, tuple] = {}
    id_sources: dict[str, tuple[pathlib.Path, dict]] = {}
    records: list[tuple[pathlib.Path, dict, str]] = []

    def signature(path: pathlib.Path) -> tuple:
        stat = path.stat(follow_symlinks=False)
        return stat.st_dev, stat.st_ino, stat.st_mode, stat.st_size, stat.st_mtime_ns

    def locate(path: pathlib.Path) -> None:
        if path not in file_states:
            file_states[path] = signature(path)

    def read(path: pathlib.Path) -> bytes:
        locate(path)
        if path not in snapshots:
            snapshots[path] = path.read_bytes()
        return snapshots[path]

    def metadata(path: pathlib.Path, text: str) -> tuple[dict | None, str]:
        data, body, _ = parse_markdown_metadata(text)
        pact = data.get("pact") if isinstance(data, dict) else None
        if pact is not None and not isinstance(pact, dict):
            raise ValueError("front matter 'pact' must be an object/table")
        if pact and isinstance(pact.get("id"), str):
            ident = pact["id"]
            prior = id_sources.get(ident)
            if prior is not None and prior[0] != path:
                errors.append(f"{path.relative_to(root)}: duplicate stable ID {ident!r} in directly referenced set")
            id_sources[ident] = (path, pact)
        return pact, body

    schema_path = root / ".pact/schema/artifact.schema.json"
    try:
        # Adopted compact runtimes load their embedded schema even when the
        # project has no source-tree .pact/schema directory.
        if schema_path.is_file():
            read(schema_path)
        schema = load_schema(schema_path)
    except Exception as exc:
        errors.append(f"cannot load artifact schema: {exc}")
        result["status"] = "fail"
        return result

    for supplied in dict.fromkeys(requested):
        try:
            # CLI paths are repository-relative or absolute paths within root.
            candidate = pathlib.Path(supplied).expanduser()
            if candidate.is_absolute():
                candidate = candidate.relative_to(root)
            path = _safe_file(root, root / "_entry", candidate.as_posix())
            relative = path.relative_to(root).as_posix()
            text = read(path).decode("utf-8")
            pact, body = metadata(path, text)
            if not pact:
                raise ValueError("explicit closure target is not a PACT Drift artifact")
            for error in validate_instance({"pact": pact}, schema):
                errors.append(f"{relative}: schema error at {error}")
            status = pact.get("status")
            if pact.get("type") != "drift":
                errors.append(f"{relative}: closure target must have type 'drift'")
            if not isinstance(pact.get("id"), str) or not pact["id"]:
                errors.append(f"{relative}: Drift requires a stable ID")
            if not isinstance(status, str) or status not in {"known", "resolved", "accepted"}:
                errors.append(f"{relative}: invalid Drift status")
            expected = f"docs/drift/{status}/" if isinstance(status, str) else ""
            if not expected or not relative.startswith(expected):
                errors.append(f"{relative}: Drift directory must match its lifecycle status")
            if status == "known":
                errors.append(f"{relative}: Drift remains known/open; no closure recorded")
            result["drifts"].append({"path": relative, "id": pact.get("id"), "status": status})
            body = _without_code(body)
            records.append((path, pact, body))
            sections, duplicates = _sections(body)
            for name in duplicates:
                errors.append(f"{relative}: duplicate section '{name}'")
            if not isinstance(status, str) or status not in {"resolved", "accepted"}:
                continue
            for name in SECTIONS:
                content = sections.get(name, "")
                if not content or _has_placeholder(content):
                    errors.append(f"{relative}: '{name}' must be nonempty and contain no template placeholders")
            if NONE_AUTHORITY.search(sections.get("Current authority", "")):
                errors.append(f"{relative}: closure requires an explicit current authority selection")
            for name in ("Conflict sources", "Decision basis", "Current authority"):
                if not _has_source_locator(sections.get(name, ""), body):
                    errors.append(f"{relative}: '{name}' requires a direct source locator (Markdown link)")
            if status == "resolved":
                implementation, _ = _sections(sections.get("Implementation and verification", ""), level=3)
                for name in ("Implementation", "Verification"):
                    content = implementation.get(name, "")
                    if not content or not _has_source_locator(content, body) or _has_placeholder(content):
                        errors.append(f"{relative}: resolved Drift requires '{name}' content and reference")
            else:
                remaining = sections.get("Remaining issues", "")
                if not remaining or re.fullmatch(r"(?:none|no(?:ne)?\.?|无|无。)", remaining, re.I):
                    errors.append(f"{relative}: accepted Drift must disclose the remaining deviation")
        except (OSError, ValueError, UnicodeError, RuntimeError) as exc:
            errors.append(f"{supplied}: {exc}")

    # Resolve only outgoing Markdown locators in the explicitly requested Drift.
    # References inside targets are intentionally not followed.
    for path, pact, body in records:
        relative = path.relative_to(root).as_posix()
        links, unsupported = _links(body)
        if unsupported:
            result["unverified"].append(f"{relative}: unsupported bracket/import syntax needs manual review")
        for raw in links:
            entry = {"source": relative, "target": raw}
            try:
                parsed = urlsplit(raw)
                if parsed.scheme or parsed.netloc:
                    if parsed.scheme in {"http", "https"} and not parsed.netloc:
                        raise ValueError("HTTP locator requires a host")
                    if parsed.scheme == "mailto" and not parsed.path:
                        raise ValueError("mailto locator requires an address")
                    if parsed.scheme not in {"http", "https", "mailto"}:
                        entry["status"] = "unsupported-scheme-unverified"
                    else:
                        entry["status"] = "remote-unverified"
                    result["unverified"].append(f"{relative}: remote or special locator {raw!r} was not fetched")
                else:
                    destination = unquote(parsed.path)
                    target = path if not destination else _safe_file(root, path, destination)
                    locate(target)
                    if target != path:
                        # Only metadata identity is parsed on direct Markdown
                        # targets; their own links/IDs do not expand this scope.
                        if target.suffix.lower() == ".md":
                            raw_bytes = read(target)
                            metadata(target, raw_bytes.decode("utf-8"))
                    entry["status"] = "local-file-located"
                    entry["path"] = target.relative_to(root).as_posix()
                    if parsed.fragment or parsed.query:
                        result["unverified"].append(f"{relative}: anchor/query in {raw!r} needs separate review")
            except (OSError, ValueError, UnicodeError, RuntimeError) as exc:
                entry["status"] = "invalid"
                errors.append(f"{relative}: cannot locate {raw!r}: {exc}")
            result["references"].append(entry)

    for path, pact, _ in records:
        for field in ("domains", "related", "supersedes", "superseded_by"):
            values = pact.get(field, [])
            if isinstance(values, str):
                values = [values]
            if not isinstance(values, list):
                continue  # Schema already reports malformed fields.
            for ident in values:
                if not isinstance(ident, str):
                    continue
                target = id_sources.get(ident)
                if target is None:
                    errors.append(f"{path.relative_to(root)}: {field} ID {ident!r} has no direct linked locator; repository was not scanned")
                elif target[0] == path:
                    errors.append(f"{path.relative_to(root)}: {field} must not reference itself")
                elif field == "domains" and target[1].get("type") != "domain":
                    errors.append(f"{path.relative_to(root)}: domains reference must target a Domain")
                elif field in {"supersedes", "superseded_by"} and target[1].get("type") != "drift":
                    errors.append(f"{path.relative_to(root)}: {field} must target the same artifact type")
    for path, original_state in file_states.items():
        try:
            if signature(path) != original_state or (
                path in snapshots and path.read_bytes() != snapshots[path]
            ):
                errors.append(f"{path.relative_to(root)}: source changed while checking; rerun required")
        except OSError as exc:
            errors.append(f"{path.relative_to(root)}: source changed while checking: {exc}")
    result["checked_paths"] = sorted(path.relative_to(root).as_posix() for path in file_states)
    result["unverified"] = list(dict.fromkeys(result["unverified"]))
    result["errors"] = list(dict.fromkeys(errors))
    result["status"] = "fail" if result["errors"] else "pass"
    return result
