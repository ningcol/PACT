#!/usr/bin/env python3
"""Build or refresh a disposable, explainable local code relationship map."""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re

from cache import cache_is_fresh, fingerprint_files, git_head
from schema_validate import load_schema, validate_instance


FORMAT_VERSION = 2

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
        or name.endswith("_test.py")
        or ".test." in name
        or ".spec." in name
    )


def discover_files(root: pathlib.Path) -> list[pathlib.Path]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
            continue
        if excluded(path, root):
            continue
        try:
            if path.stat().st_size > 1_000_000:
                continue
        except OSError:
            continue
        files.append(path)
    return sorted(files)


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
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append(node.name)
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


def resolve_relative_js(
    spec: str,
    source: pathlib.Path,
    available: set[pathlib.Path],
) -> tuple[pathlib.Path | None, str | None]:
    if not spec.startswith("."):
        return None, None

    base = (source.parent / spec).resolve()
    candidates = [base]

    for ext in EXTENSIONS:
        candidates.append(pathlib.Path(str(base) + ext))

    for ext in EXTENSIONS:
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
    # Relative imports are explicit in the AST and resolved against the source package.
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

    # Absolute imports depend on Python environment/sys.path. A repository-local
    # alias match is useful generated evidence, but remains heuristic.
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
        language = EXTENSIONS[path.suffix.lower()]
        relative = rel(path, root)
        imports = []

        if language == "python":
            symbols, raw_imports = parse_python(path)
            for raw, level in raw_imports:
                resolved, confidence = resolve_python(raw, level, path, root, module_map)
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
        else:
            symbols, raw_imports = parse_js_like(path)
            for raw in raw_imports:
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
            "symbols": symbols,
            "imports": imports,
            "is_test": is_test_path(relative),
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

    paths = discover_files(root)
    source_fingerprint = fingerprint_files(root, paths)

    if args.ensure and cache_is_fresh(
        output,
        format_version=FORMAT_VERSION,
        source_fingerprint=source_fingerprint,
    ):
        print(f"PACT code-map: fresh -> {output}")
        return 0

    data = build_code_map(root, paths, source_fingerprint)

    schema_path = root / ".pact" / "schema" / "code-map.schema.json"
    if schema_path.exists():
        errors = validate_instance(data, load_schema(schema_path))
        if errors:
            for error in errors:
                print(f"PACT code-map schema error: {error}")
            return 2

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"PACT code-map: {len(data['files'])} source file(s), "
        f"{len(data['edges'])} resolved local import edge(s) -> {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
