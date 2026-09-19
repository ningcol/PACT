# Contributing to PACT

PACT should get **smaller, more trustworthy, and easier to operate** as it evolves.

Before adding a new command, schema, metadata field, language adapter, or workflow, ask whether an existing primitive can solve the same problem.

## Development requirements

PACT core requires:

- Python 3.11+;
- Git for Git-aware tests/features;
- no third-party Python runtime dependencies.

Run the core checks:

```bash
python3 pact.py --help
python3 scripts/pact/pact.py schema-lint
python3 scripts/pact/pact.py workflow-lint
python3 scripts/pact/pact.py check
python3 -m unittest discover -s scripts/pact/tests -p "test_*.py"
```

## Design rules

Preserve these boundaries:

1. Product Truth is not inferred from code alone.
2. Deterministic facts may FAIL; semantic guesses must remain review/warnings.
3. Generated indexes/maps are disposable derived evidence, never authority.
4. Framework-managed files and project-owned seed/truth files stay separate.
5. Owner-facing output describes behavior/consequence/evidence before implementation detail.
6. New orchestration must not remove low-level primitives or unnecessarily constrain stronger future agents.
7. Runtime schema constraints must be enforced by the stdlib validator; `schema-lint` must reject unsupported keywords.
8. Do not add runtime dependencies merely for convenience without demonstrating that stdlib implementation is materially insufficient.

## Tests

A change should add the smallest test that proves the boundary being changed.

Relevant layers include:

- **PACT Check** — the full Ubuntu/Python 3.12 correctness gate; it runs every `test_*.py` plus command/smoke/end-to-end checks;
- deterministic unit tests;
- temporary brownfield init/upgrade tests;
- **Core Matrix** — the 3 OS × 3 Python portability gate; keep it focused on bootstrap/runtime/distribution/stdlib/init/Git-path behavior instead of repeating the full semantic suite nine times;
- external public-repository pilots when a change affects Discovery, installation, code maps, or unsupported-language behavior.

Heavy external pilots are manual regressions and should not run on every pull request.

## Pull requests

Keep PRs narrow enough that a failure can be attributed to one design boundary.

Useful PR descriptions explain:

- what user/agent problem changes;
- what remains deliberately out of scope;
- deterministic vs semantic behavior;
- evidence added for the change;
- compatibility/migration impact.

## Licensing

PACT's repository license is an explicit owner decision. Until a license is selected, do not assume public visibility alone grants downstream redistribution rights beyond GitHub's platform terms.
