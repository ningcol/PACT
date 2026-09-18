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
