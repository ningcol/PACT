# Code-aware Generated Relationships

PACT v1.1 extends Project Discovery with a rebuildable code map.

The code map is **derived evidence**, never Product Truth.

## v1.1 scope

Structured source families:

- Python;
- JavaScript / JSX;
- TypeScript / TSX;
- Vue single-file components.

Generic lexical fallback source families:

- Go;
- Swift;
- Kotlin;
- Java;
- Rust;
- C / C++;
- C#;
- Ruby;
- PHP.

Structured files may provide top-level symbols, direct Python class-method symbols, import statements, resolved local import edges, and test-file classification.

Generic files provide only:

- source file path;
- language;
- bounded lexical identifiers (maximum 256);
- test-file classification.

Generic lexical fallback deliberately does **not** claim AST structure, imports, call relationships, or behavioral dependencies.

## Confidence boundary

Generated relationships explicitly carry confidence rather than pretending all resolution is equally certain. Generic lexical identifiers are not relationships at all; they are low-confidence search evidence only.

Structured relationship confidence:

- `relative-resolved` — relative JS/TS/Vue import resolved to a repository file;
- `ast-resolved` — Python relative import resolved using AST + package position;
- `heuristic` — repository-local Python absolute import match; actual runtime `sys.path` may differ;
- unresolved imports remain unresolved.

Even a high-confidence structural edge means only:

> file A has a generated structural relationship to file B.

It does **not** mean:

> changing B definitely changes product behavior.

Impact Analysis therefore exposes import neighbors as **code candidates**, not deterministic product impacts.

## Freshness

Project Map and Code Map store a source fingerprint. Discovery/Context/Impact/Explain reuse a cached map only while that fingerprint still matches the repository source set.

This avoids both stale indexes and unconditional full reparsing on every query.

Cache freshness also verifies index structure, not just a matching `format_version` and `source_fingerprint`. Project Map checks its required document/ID fields against the visible source-document set. Code Map checks the existing Code Map JSON Schema, repository root and visible code-path set, and confirms its generated edges match the per-file resolved imports. Truncated/malformed but otherwise valid JSON is rebuilt, not treated as a zero-hit index. The Git HEAD is stored as metadata, not part of the source-content fingerprint.

## Unresolved imports

PACT does not guess unsupported resolution rules.

Examples that may remain unresolved:

- project-specific TS path aliases;
- framework magic imports;
- runtime plugin registries;
- dynamic routing conventions;
- reflection/string-based loading.

Future adapters may add project-specific resolvers. Until then, generic lexical fallback helps locate candidate files without fabricating those missing relationships.

## Search

`pact discover --code` adds ranked code results based on:

- path;
- file name;
- extracted symbol names;
- raw import names;
- lower-weight bounded generic identifiers for unsupported structured languages.

Structured symbol matches (including direct Python class methods) rank above generic identifier matches. Direct lexical matches are ranked ahead of one-hop import neighbors. With a final code-result budget of one, a direct match always takes the slot; for larger budgets, import neighbors can appear only after reserving at least the best direct match. This affects selection, not the underlying lexical scores.

## Impact

`pact impact --code` adds code-neighbor candidates:

- imports changed file;
- imported by changed file;
- related test/import edges.

These candidates help Context Resolution decide where to inspect next. They do not change authority or Product Truth.


## Adopted-project ownership boundary

When PACT is installed into another repository, generated Project/Code maps consult `.pact/install.json`.

- framework-managed PACT files are excluded from target discovery;
- project-owned seed files are excluded while byte-identical to their installed scaffold;
- once a seed file is edited by the project, it becomes discoverable project knowledge;
- a PACT source checkout without an install manifest continues indexing itself normally.

This prevents PACT's own runtime, generic governance scaffolding, and Skills from being mistaken for the target product/codebase.


## Large-repository enumeration

PACT prefers Git-aware enumeration when the target is a Git worktree:

```text
git ls-files -co --exclude-standard
```

This returns tracked files plus visible untracked files while respecting repository ignore rules. PACT therefore does not pay the filesystem traversal cost for ignored dependency/build trees merely to discard them later.

When Git is unavailable, PACT falls back to `os.walk` with directory pruning before descent.

## Per-file incremental parsing

Whole-map freshness still uses a source fingerprint.

When the fingerprint changes, PACT does **not** automatically reparse every source file.

It keeps a disposable per-file parse cache keyed by:

- repository-relative path;
- file size;
- nanosecond modification time;
- SHA256 of source bytes;
- parser-cache version and a self-integrity digest over the cached parsed payload.

Unchanged files reuse parsed symbols/raw imports. Changed/new files are reparsed; removed files are dropped. Global import resolution/edges are then rebuilt from these cheap cached parse results.

The same model is used for Project Map Markdown parsing.

This cache is never authority. Removing `.pact/cache/` must always restore a correct full rebuild.

## Cache write and integrity boundary

Project Map, Code Map and per-file parse caches are written through a shared stdlib-only atomic JSON publisher. Each writer prepares a complete JSON payload in its own uniquely named temporary file in the destination directory, flushes and fsyncs it, then atomically replaces the destination. If publication fails, an existing cache file remains intact and temporary data is cleaned up. Multiple writers may each publish a complete snapshot; the latest completed replacement wins. One reader sees a complete old or new snapshot, not a half-written JSON document.

This atomicity applies to **one file only**. Project Map, Code Map and per-file parse caches do not form a joint transaction, and a concurrent source edit may invalidate a previously computed fingerprint; the next freshness check repairs stale output. The cache payload digest detects accidental changes, not an attacker with the ability to rewrite both parsed data and its digest. Neither local caches nor generated import relationships become proof of product behavior.
