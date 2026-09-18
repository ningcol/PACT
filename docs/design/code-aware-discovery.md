# Code-aware Generated Relationships

PACT v1.1 extends Project Discovery with a rebuildable code map.

The code map is **derived evidence**, never Product Truth.

## v1.1 scope

Supported source families:

- Python;
- JavaScript / JSX;
- TypeScript / TSX;
- Vue single-file components for import extraction.

Generated facts:

- source file path;
- top-level symbols where cheaply extractable;
- import statements;
- resolved local import edges;
- test-file classification.

## Confidence boundary

Generated relationships explicitly carry confidence rather than pretending all resolution is equally certain:

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

## Unresolved imports

PACT does not guess unsupported resolution rules.

Examples that may remain unresolved:

- project-specific TS path aliases;
- framework magic imports;
- runtime plugin registries;
- dynamic routing conventions;
- reflection/string-based loading.

Future adapters may add project-specific resolvers.

## Search

`pact discover --code` adds ranked code results based on:

- path;
- file name;
- extracted symbol names;
- raw import names.

Direct lexical matches are ranked ahead of one-hop import neighbors.

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
- parser-cache version.

Unchanged files reuse parsed symbols/raw imports. Changed/new files are reparsed; removed files are dropped. Global import resolution/edges are then rebuilt from these cheap cached parse results.

The same model is used for Project Map Markdown parsing.

This cache is never authority. Removing `.pact/cache/` must always restore a correct full rebuild.
