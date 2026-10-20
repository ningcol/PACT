#!/usr/bin/env python3
"""Build or incrementally refresh a disposable local code relationship map."""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import sys

from cache import atomic_write_json, cache_is_fresh, fingerprint_files, git_head
from distribution import discovery_excluded_paths
from parse_cache import parse_with_cache
from repository_files import repository_files
from schema_validate import load_schema, validate_instance


FORMAT_VERSION = 4
PARSE_CACHE_VERSION = 3

DEFAULT_EXCLUDES = {
    ".git",
    ".hg",
    ".svn",
    ".pact/cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".next",
    "out",
    "vendor",
    "__pycache__",
}

EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".vue": "vue",
    ".go": "go",
    ".swift": "swift",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".java": "java",
    ".rs": "rust",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
}

STRUCTURED_LANGUAGES = {
    "python",
    "javascript",
    "typescript",
    "vue",
}

JS_RESOLVE_EXTENSIONS = (
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".vue",
)

GENERIC_IDENTIFIER = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b")
GENERIC_C_LIKE_NONCODE = re.compile(
    r'''(?:
        //[^
]* |
        /\*.*?\*/ |
        "(?:\\.|[^"\\])*" |
        '(?:\\.|[^'\\])*' |
        `(?:\\.|[^`\\])*`
    )''',
    re.DOTALL | re.VERBOSE,
)
GENERIC_IDENTIFIER_LIMIT = 256
GENERIC_STOPWORDS = {
    "break", "case", "catch", "class", "const", "continue", "default",
    "defer", "else", "enum", "false", "finally", "for", "func", "function",
    "if", "import", "interface", "let", "match", "new", "nil", "null",
    "package", "private", "protected", "public", "return", "static", "struct",
    "switch", "this", "throw", "true", "try", "type", "var", "while",
}

JS_IMPORT = re.compile(
    r"""(?:
        import\s+(?:[^'"]*?\s+from\s+)?|
        export\s+[^'"]*?\s+from\s+|
        require\s*\(\s*|
        import\s*\(\s*
    )['"]([^'"]+)['"]""",
    re.VERBOSE,
)

JS_SYMBOL = re.compile(
    r"""(?:^|\n)\s*(?:export\s+)?(?:
        (?:async\s+)?function\s+([A-Za-z_$][\w$]*)|
        class\s+([A-Za-z_$][\w$]*)|
        (?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=
    )""",
    re.VERBOSE,
)


def rel(path: pathlib.Path, root: pathlib.Path) -> str:
    return path.relative_to(root).as_posix()


def excluded(path: pathlib.Path, root: pathlib.Path) -> bool:
    relative = rel(path, root)
    parts = pathlib.PurePosixPath(relative).parts
    for name in DEFAULT_EXCLUDES:
        if "/" in name:
            if relative.startswith(name + "/") or relative == name:
                return True
        elif name in parts:
            return True
    return False


def is_test_path(relative: str) -> bool:
    path = pathlib.PurePosixPath(relative)
    name = path.name.lower()
    parts = {part.lower() for part in path.parts}
    return (
        "tests" in parts
        or "test" in parts
        or "__tests__" in parts
        or name.startswith("test_")
        or "_test." in name
        or ".test." in name
        or ".spec." in name
    )


def discover_files(root: pathlib.Path) -> tuple[list[pathlib.Path], str]:
    files: list[pathlib.Path] = []
    excluded_paths = discovery_excluded_paths(root)
    visible, enumeration_mode = repository_files(root)

    for path in visible:
        if path.suffix.lower() not in EXTENSIONS:
            continue
        if excluded(path, root):
            continue
        if rel(path, root) in excluded_paths:
            continue
        try:
            if path.stat().st_size > 1_000_000:
                continue
        except OSError:
            continue
        files.append(path)

    return sorted(files), enumeration_mode


def python_module_aliases(path: pathlib.Path, root: pathlib.Path) -> list[str]:
    relative = path.relative_to(root).with_suffix("")
    parts = list(relative.parts)
    aliases = []

    if parts and parts[-1] == "__init__":
        parts = parts[:-1]

    if parts:
        aliases.append(".".join(parts))
        # Bare-name aliases are convenient but ambiguous across packages.
        aliases.append(parts[-1])

    return list(dict.fromkeys(alias for alias in aliases if alias))


def parse_python(path: pathlib.Path) -> tuple[list[str], list[tuple[str, int]]]:
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
    except (UnicodeDecodeError, SyntaxError):
        return [], []

    symbols = []
    imports: list[tuple[str, int]] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(node.name)
        elif isinstance(node, ast.ClassDef):
            symbols.append(node.name)
            # Direct class methods are stable retrieval handles (for example
            # Service.dispatch) without recursively indexing local closures.
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(member.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, 0))
        elif isinstance(node, ast.ImportFrom):
            imports.append((node.module or "", node.level))

    return sorted(set(symbols)), imports


def parse_js_like(path: pathlib.Path) -> tuple[list[str], list[str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [], []

    imports = JS_IMPORT.findall(text)
    symbols = []
    for match in JS_SYMBOL.finditer(text):
        symbol = next((group for group in match.groups() if group), None)
        if symbol:
            symbols.append(symbol)

    return sorted(set(symbols)), list(dict.fromkeys(imports))


def parse_generic_identifiers(path: pathlib.Path) -> list[str]:
    """Bounded code-like lexical fallback; no AST/import semantics are implied."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    # Remove common C/Go/Java/Swift-style comments and quoted strings so
    # prose/examples do not dominate the bounded identifier budget. This is a
    # lexical noise filter, not a language parser.
    text = GENERIC_C_LIKE_NONCODE.sub(" ", text)

    seen: set[str] = set()
    identifiers: list[str] = []
    for match in GENERIC_IDENTIFIER.finditer(text):
        value = match.group(0)
        if value.casefold() in GENERIC_STOPWORDS or value in seen:
            continue
        seen.add(value)
        identifiers.append(value)
        if len(identifiers) >= GENERIC_IDENTIFIER_LIMIT:
            break
    return identifiers


def parse_source(path: pathlib.Path, root: pathlib.Path) -> dict:
    language = EXTENSIONS[path.suffix.lower()]
    relative = rel(path, root)

    identifiers: list[str] = []
    parser_mode = "structured"

    if language == "python":
        symbols, raw_imports = parse_python(path)
        imports = [
            {"raw": raw, "level": int(level)}
            for raw, level in raw_imports
        ]
    elif language in {"javascript", "typescript", "vue"}:
        symbols, raw_imports = parse_js_like(path)
        imports = [
            {"raw": raw, "level": 0}
            for raw in raw_imports
        ]
    else:
        symbols = []
        imports = []
        identifiers = parse_generic_identifiers(path)
        parser_mode = "generic-lexical"

    return {
        "language": language,
        "parser_mode": parser_mode,
        "symbols": symbols,
        "identifiers": identifiers,
        "raw_imports": imports,
        "is_test": is_test_path(relative),
    }


def resolve_relative_js(
    spec: str,
    source: pathlib.Path,
    available: set[pathlib.Path],
) -> tuple[pathlib.Path | None, str | None]:
    if not spec.startswith("."):
        return None, None

    base = (source.parent / spec).resolve()
    candidates = [base]

    for ext in JS_RESOLVE_EXTENSIONS:
        candidates.append(pathlib.Path(str(base) + ext))

    for ext in JS_RESOLVE_EXTENSIONS:
        candidates.append(base / ("index" + ext))

    for candidate in candidates:
        if candidate in available:
            return candidate, "relative-resolved"
    return None, None


def resolve_python(
    raw: str,
    level: int,
    source: pathlib.Path,
    root: pathlib.Path,
    module_map: dict[str, pathlib.Path],
) -> tuple[pathlib.Path | None, str | None]:
    if level:
        package = list(source.relative_to(root).with_suffix("").parts[:-1])
        up = max(level - 1, 0)
        if up:
            package = package[:-up] if up <= len(package) else []
        module_parts = [part for part in raw.split(".") if part]
        candidate = ".".join(package + module_parts)
        if candidate in module_map:
            return module_map[candidate], "ast-resolved"
        return None, None

    # Absolute imports depend on Python environment/sys.path. Repository-local
    # matches remain heuristic generated evidence.
    if raw in module_map:
        return module_map[raw], "heuristic"

    parts = raw.split(".")
    while len(parts) > 1:
        parts.pop()
        candidate = ".".join(parts)
        if candidate in module_map:
            return module_map[candidate], "heuristic"

    target = module_map.get(raw.split(".")[-1])
    return (target, "heuristic") if target else (None, None)


def build_code_map(
    root: pathlib.Path,
    paths: list[pathlib.Path],
    parsed_sources: dict[str, dict],
    source_fingerprint: str,
) -> dict:
    available = {path.resolve() for path in paths}

    module_map: dict[str, pathlib.Path] = {}
    ambiguous_aliases: set[str] = set()
    for path in paths:
        if path.suffix.lower() != ".py":
            continue
        for alias in python_module_aliases(path, root):
            resolved = path.resolve()
            previous = module_map.get(alias)
            if previous and previous != resolved:
                ambiguous_aliases.add(alias)
            else:
                module_map[alias] = resolved

    for alias in ambiguous_aliases:
        module_map.pop(alias, None)

    files = []
    edges = []

    for path in paths:
        relative = rel(path, root)
        parsed = parsed_sources[relative]
        language = parsed["language"]
        imports = []

        if language == "python":
            for item in parsed["raw_imports"]:
                raw = item["raw"]
                level = int(item.get("level", 0))
                resolved, confidence = resolve_python(
                    raw,
                    level,
                    path,
                    root,
                    module_map,
                )
                resolved_rel = rel(resolved, root) if resolved else None
                imports.append({
                    "raw": ("." * level) + raw,
                    "resolved": resolved_rel,
                    "confidence": confidence,
                })
                if resolved_rel and resolved_rel != relative:
                    edges.append({
                        "from": relative,
                        "to": resolved_rel,
                        "kind": "import",
                        "confidence": confidence,
                    })
        elif language in {"javascript", "typescript", "vue"}:
            for item in parsed["raw_imports"]:
                raw = item["raw"]
                resolved, confidence = resolve_relative_js(raw, path, available)
                resolved_rel = rel(resolved, root) if resolved else None
                imports.append({
                    "raw": raw,
                    "resolved": resolved_rel,
                    "confidence": confidence,
                })
                if resolved_rel and resolved_rel != relative:
                    edges.append({
                        "from": relative,
                        "to": resolved_rel,
                        "kind": "import",
                        "confidence": confidence,
                    })

        files.append({
            "path": relative,
            "language": language,
            "parser_mode": parsed["parser_mode"],
            "symbols": parsed["symbols"],
            "identifiers": parsed.get("identifiers", []),
            "imports": imports,
            "is_test": bool(parsed["is_test"]),
        })

    unique = {
        (edge["from"], edge["to"], edge["kind"], edge["confidence"]): edge
        for edge in edges
    }

    return {
        "format_version": FORMAT_VERSION,
        "root": ".",
        "source_fingerprint": source_fingerprint,
        "git_head": git_head(root),
        "files": files,
        "edges": [unique[key] for key in sorted(unique)],
    }


def valid_code_index(
    data: dict, *, schema: dict, expected_paths: set[str],
    root: pathlib.Path, paths: list[pathlib.Path],
) -> bool:
    """Reuse only a complete, schema-valid index over current source paths."""
    if data.get("root") != "." or validate_instance(data, schema):
        return False
    files = data["files"]
    actual_paths = {entry["path"] for entry in files}
    if len(actual_paths) != len(files) or actual_paths != expected_paths:
        return False

    # Import records and the generated edge table are two views of the same
    # parsed relationships. A schema-valid empty edge table can otherwise
    # silently erase all import-neighbor discovery.
    expected_edges = set()
    for entry in files:
        for item in entry["imports"]:
            related = item["resolved"]
            if related is not None:
                if related not in actual_paths:
                    return False
                if related != entry["path"]:
                    expected_edges.add(
                        (entry["path"], related, "import", item["confidence"])
                    )

    observed_edges = {
        (edge["from"], edge["to"], edge["kind"], edge["confidence"])
        for edge in data["edges"]
    }
    if len(observed_edges) != len(data["edges"]) or observed_edges != expected_edges:
        return False

    # Cache file digests, valid schemas and self-checksums do not authenticate
    # lexical metadata. Reparse source once before declaring a cache hit so a
    # forged symbol/import/identifier cannot redirect Agent navigation.
    authoritative = {
        rel(path, root): parse_source(path, root)
        for path in paths
    }
    canonical = build_code_map(root, paths, authoritative, data["source_fingerprint"])
    return data["files"] == canonical["files"] and data["edges"] == canonical["edges"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build generated PACT code relationship map")
    parser.add_argument("--root", help="repository root; defaults to this script's repository")
    parser.add_argument("--output", default=".pact/cache/code-map.json")
    parser.add_argument(
        "--ensure",
        action="store_true",
        help="reuse the existing code map when its source fingerprint is current",
    )
    args = parser.parse_args()

    default_root = pathlib.Path(__file__).resolve().parents[2]
    root = pathlib.Path(args.root).expanduser().resolve() if args.root else default_root
    output = pathlib.Path(args.output)
    if not output.is_absolute():
        output = root / output

    schema_path = root / ".pact" / "schema" / "code-map.schema.json"
    try:
        schema = load_schema(schema_path)
    except Exception as exc:
        print(f"PACT code-map: cannot load schema: {exc}", file=sys.stderr)
        return 2

    # Source files are not part of the atomic JSON publication. Re-enumerate
    # and re-hash the COMPLETE code source set after parsing/building, including
    # the healthy-cache path, so no mixed-generation index is published.
    for attempt in range(3):
        try:
            paths, enumeration_mode = discover_files(root)
            source_fingerprint = fingerprint_files(root, paths)
            expected_paths = {rel(path, root) for path in paths}

            fresh = args.ensure and cache_is_fresh(
                output,
                format_version=FORMAT_VERSION,
                source_fingerprint=source_fingerprint,
                validator=lambda data: valid_code_index(
                    data, schema=schema, expected_paths=expected_paths,
                    root=root, paths=paths,
                ),
            )
            if not fresh:
                parse_cache_path = root / ".pact" / "cache" / "code-file-cache.json"
                parsed_sources, stats = parse_with_cache(
                    root=root,
                    paths=paths,
                    cache_path=parse_cache_path,
                    cache_version=PARSE_CACHE_VERSION,
                    parser=lambda path: parse_source(path, root),
                )
                if set(parsed_sources) != expected_paths:
                    raise OSError("code source set changed while parsing")

                # Parsing caches are disposable and not a source of truth.
                # Reparse even if a cache writer recomputed its own checksum.
                for path in paths:
                    relative = rel(path, root)
                    canonical = parse_source(path, root)
                    if parsed_sources[relative] != canonical:
                        parsed_sources[relative] = canonical

                data = build_code_map(
                    root, paths, parsed_sources, source_fingerprint,
                )

            updated_paths, updated_mode = discover_files(root)
            if (
                [rel(path, root) for path in updated_paths]
                != [rel(path, root) for path in paths]
                or updated_mode != enumeration_mode
                or fingerprint_files(root, updated_paths) != source_fingerprint
            ):
                raise OSError("source files changed during Code Map scan")

            if fresh:
                print(f"PACT code-map: fresh -> {output}")
                return 0

            errors = validate_instance(data, schema)
            if errors:
                for error in errors:
                    print(f"PACT code-map schema error: {error}", file=sys.stderr)
                return 2

            # Recheck once more after graph generation/validation and before
            # publication, not just after parsing the last source file.
            final_paths, final_mode = discover_files(root)
            if (
                [rel(path, root) for path in final_paths]
                != [rel(path, root) for path in paths]
                or final_mode != enumeration_mode
                or fingerprint_files(root, final_paths) != source_fingerprint
            ):
                raise OSError("source files changed before Code Map publication")

            atomic_write_json(output, data)
            print(
                f"PACT code-map: {len(data['files'])} source file(s), "
                f"{len(data['edges'])} resolved local import edge(s) "
                f"[enumeration={enumeration_mode}, parsed={stats['parsed']}, "
                f"reused={stats['reused']}, removed={stats['removed']}] -> {output}"
            )
            return 0
        except OSError as exc:
            if attempt == 2:
                print(
                    f"PACT code-map: unstable source snapshot after 3 attempts: {exc}",
                    file=sys.stderr,
                )
                return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
