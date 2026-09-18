# PACT Checking Model

PACT intentionally separates deterministic enforcement from semantic review.

## Deterministic checks

These may block CI because the machine can establish them reliably:

- malformed machine-readable artifact metadata;
- duplicate durable IDs;
- missing local Stable-ID references;
- invalid Domain-reference target type;
- invalid lifecycle state or lifecycle-directory mismatch;
- artifact type in an invalid repository location;
- broken resolvable internal Markdown links;
- broken generated artifacts when generation is deterministic;
- forbidden dependency when a fitness function exists;
- failed tests.

Current implementation:

```bash
python -m pip install -r scripts/pact/requirements.txt
python scripts/pact/check.py
```

## Semantic checks

These should not become hard failures merely because an LLM or heuristic suspects them:

- architecture may be stale;
- product rule may be affected by a code change;
- a durable decision may be missing;
- two documents may represent conflicting product meaning;
- implementation may have introduced unrequested behavior.

These belong to Convergence Review and produce findings such as:

```text
aligned
stale
missing
partial
contradicts
unrequested
owner-decision
```

## Policy

**If a machine can establish the fact, FAIL. If it can only infer, WARN/review.**

Referential integrity is deterministic: an explicit local ID/link either resolves or it does not.

Semantic correctness is not: a resolved Rule may still be obsolete or irrelevant, which remains a Convergence concern.

This protects PACT from becoming a documentation-compliance system that developers and agents satisfy with low-value paperwork.
