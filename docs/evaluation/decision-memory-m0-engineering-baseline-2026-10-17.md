# M0 — Decision-memory deterministic baseline and scoped fixes (2026-10-17)

> **PACT only. Engineering source tests are not a real Agent/Owner trial.**
> Original baseline: `b0eccb0b6315cf22cf8fdc19fad57ff901ba1160`.
> This report does **not** certify general semantic Decision recall, approval
> provenance, or prevent all future Agent decision drift.

## What independent review established — and what it did not

The prior [independent design review](https://github.com/ningcol/PACT/pull/216)
reported **four P1 design risks** (unverifiable Owner approval, partial Decision
supersession, pathless Decision recall, stale code-path anchors after rename)
and **one P2 study-design risk** (missing frozen stop/cost gates). These were
document-level concerns, **not five reproduced runtime bugs**.

The first M0 source investigation identified **two concrete deterministic
implementation gaps** and made them reproducible with disposable PACT fixtures:

| Reproduced failure on pre-fix main | Scope | Minimum change |
| --- | --- | --- |
| `map.parse_document` drops `supersedes` / `superseded_by` metadata | Source/derived index loses explicit Decision lineage | Preserve existing fields and invalidate old Project Map and per-file parse-cache generations |
| `check.validate_artifacts` verifies individual linked IDs but accepts cyclic Decision `supersedes` relationships | Impossible Decision history can pass a deterministic check | Reject cycles using existing explicit ID links, without interpreting natural-language validity |

**Actual RED:** [PACT Check #38995715536](https://github.com/ningcol/PACT/actions/runs/38995715536)
on test-only head `3d44a08cd5ae456ed0bb661a873334b52d8fcec2`:
408 tests run, **one failure and one error**, specifically the missing
`supersedes` Project Map field and accepted `DEC-A ⇄ DEC-B` supersession
cycle. The third regression requires legitimate one-way legacy relationships
to keep passing. This is new M0 RED evidence, not a reconstruction of the
original S0–S7 pre-existing RED acceptance criteria.

## Contained implementation and regression scope

- Only the PACT Project Map cache/index path, deterministic artifact checker,
  focused PACT unit regressions and this engineering report are changed.
- Project Map `format_version` 4 → 5 and per-file parse cache 1 → 2
  prevent source-unchanged old parse records from hiding the new fields.
  Code Map format and compact Task Context/Task Contract schemas are unchanged.
- Decision cycle detection uses existing `supersedes` and
  `superseded_by` values; consistent forward/reverse references produce the
  same directed edge. Legacy one-way links remain allowed. A passing
  acyclicity check is **not evidence that partially replaced natural-language
  constraints were carried forward**.
- Installed `pact.pyz` source tests and release smoke must accompany source
  checks; the runtime is built from maintained stdlib modules.

## Remaining concerns — not silently marked fixed

1. **Owner approval provenance:** no authenticated approval service or
   owner-signature claim is implemented; `owners` metadata and Markdown
   prose are not proof of approval. Continue using existing Owner authority
   boundaries, and do not machine-assert `owner-approved`.
2. **Partial supersession semantics:** preserving lineage does not tell a
   machine which individual natural-language constraint survived; present
   old/new rationale for human/Agent semantic reconciliation.
3. **Pathless and vocabulary-disjoint Decision retrieval:** PACT cannot
   guarantee discovery without explicit ID, alias, domain, link or path
   association. Empty results must not imply no constraints.
4. **Path rename/move lifecycle:** stale `paths` and new destination-only
   cold-start retrieval require separate measurable M0 fixtures and an A/B
   necessity assessment before considering automatic path migration.
5. **Cost/stop gates:** evaluate simple document-only A and explicit-ID B
   before building default C scanning; no independent held-out Agent/Owner
   benefit has been observed in this M0 task.

## Go/no-go after scoped engineering closure

Confirm focused regression tests, full PACT Check, genuine fail-fast
Ubuntu/macOS/Windows × Python 3.11–3.13 matrix, and built compact-runtime
smoke on the exact resulting source. Then retain **M0 still open for actual
A/B/C retrieval-benefit assessment**; do not call the larger V3 initiative
completed based on these two fixes. Release stays HOLD; no tag, GitHub
Release, or edits outside `ningcol/PACT`.
