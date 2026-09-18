# PACT Artifact Model

PACT uses a small set of durable artifact types. The goal is not to add metadata everywhere; the goal is to make the few important artifacts discoverable and machine-checkable.

## 1. Artifact types

| Type | Purpose | Durable? | Typical location |
| --- | --- | --- | --- |
| `domain` | Business concept landing page / router | yes | `docs/product/domains/` |
| `rule` | Confirmed normative product rule | yes | `docs/product/rules/` |
| `decision` | Durable engineering rationale | yes | `.agents/decisions/` |
| `change` | Active/completed change intent | temporary-to-historical | `docs/changes/` |
| `drift` | Known unresolved inconsistency | temporary | `docs/drift/` |
| `architecture` | Current architecture view | yes, current-state | `docs/architecture/` |

Do not assign PACT metadata to ordinary source files, tests, comments, or trivial docs.

## 2. Stable IDs

Stable IDs are required only for durable artifacts that other artifacts may reference.

Recommended patterns:

```text
DOMAIN-<NAME>
RULE-<DOMAIN>-NNN
DEC-<AREA>-NNN
INV-<AREA>-NNN
DRIFT-NNN
```

IDs should survive file renames and directory moves.

## 3. Front matter

Durable PACT artifacts should use YAML front matter.

Example:

```yaml
---
pact:
  type: rule
  id: RULE-BATCH-001
  status: confirmed
  owners:
    - product
  domains:
    - DOMAIN-BATCH
  related:
    - DEC-BATCH-002
  verification:
    - e2e/batch-switch.spec.ts
---
```

Only fields that carry durable meaning should be added.

## 4. Common fields

- `type`: artifact kind.
- `id`: stable identifier when required.
- `status`: lifecycle state appropriate to the artifact type.
- `owners`: authority category, not a person's name by default.
- `domains`: canonical business concepts affected.
- `related`: stable IDs of related durable artifacts.
- `verification`: test/evidence entry points when durable and useful.

## 5. Lifecycle

### Rule

```text
candidate → confirmed → superseded | retired
```

A candidate rule is not normative Product Truth.

### Decision

```text
proposed → implemented | rejected
implemented → superseded | archived
```

### Change

```text
active → completed | abandoned
```

### Drift

```text
known → resolved | accepted
```

## 6. Reference policy

Use stable IDs to reference durable semantics.

Use repository paths to reference current implementation or generated evidence.

Do not copy rule text or decision rationale into multiple artifacts merely to make them searchable.

## 7. Machine checks

PACT v1 should hard-fail only deterministic violations:

- malformed PACT front matter;
- missing required ID for durable artifact types;
- duplicate stable IDs;
- invalid lifecycle status;
- invalid type/path combination;
- broken explicit stable-ID references where reliably resolvable.

PACT v1 should warn, not fail, for semantic guesses:

- a rule may have become stale;
- a decision may be missing;
- an architecture document may no longer match code;
- a product domain may be affected by a diff.

Semantic checks belong to Convergence Review.
