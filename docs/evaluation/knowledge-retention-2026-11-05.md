# PACT knowledge retention / domain audit: three-round real-source engineering replay

**Date:** 2026-11-05. **PACT PR:** [#249](https://github.com/ningcol/PACT/pull/249).  
**Reproducible run:** [Actions #41979425967](https://github.com/ningcol/PACT/actions/runs/41979425967) (PACT commit `f01f3e2f53df6afd57d30cd8c9ba2c5e4495dd65`; subsequent PR commits require their own checks).  
**External public source:** [mrwilson/adr-viewer](https://github.com/mrwilson/adr-viewer), pinned `a25f1c71e031bdaa63fe3175f969f197139f2044`.

## Scope and evidence boundary

The cloned repository and its original six ADRs are real, immutable test inputs. The replay adapts existing source-authored ADRs into **test-only** PACT Decision records inside a disposable GitHub Actions clone. The task sequence and candidate Domain are **developer-authored**, not an independent holdout, and neither a real Agent nor an Owner is exercised. No external repository is pushed or changed; the source checkout's tracked files remain clean.

This is a **three-round mechanical maintenance rehearsal**, not a long-term field trial or a proof that AI Agents obey project decisions. It explicitly records `agent_decision_obedience_verified = false`, `retrieval_improvement_proven = false` and `long_term_effectiveness_proven = false`.

## Frozen replay sequence

1. **No new durable knowledge:** inspect a frozen real-ADR task question and review the existing six adapted Decision records; retain `none` without writing another note.
2. **Create a navigation entry:** add one **candidate** Domain router with a reference to upstream-derived current Decision `DEC-ADR-0004`; retain `create`. A candidate Domain is not Owner-confirmed Product Truth.
3. **Update existing navigation:** add the explicit superseded historical Decision `DEC-ADR-0003` to the *same* Domain router; retain `update`, without adding a parallel note.

All stages use the installed compact runtime, `pact audit`, `pact discover`, and `pact check` on the disposable real-source clone, with a task-delta check of the declared retention paths. No raw test case text or developer oracle is elevated to Product Truth.

## Observed engineering results

| Measure | Round 1: none | Round 2: create | Round 3: update |
| --- | ---: | ---: | ---: |
| Source-derived Decision files | 6 | 6 | 6 |
| Confirmed Product Rule files | 0 | 0 | 0 |
| Test-only candidate Domain files | 0 | 1 | 1 |
| Possible overlap candidates | 0 | 0 | 0 |
| Confirmed Domain alias collisions | 0 | 0 | 0 |
| Deterministic audit | PASS | PASS | PASS |
| Retention review | reviewed / none | reviewed / create | reviewed / update |

The same frozen task query retrieved `DEC-ADR-0004` and historical `DEC-ADR-0003` both **before** and **after** router creation; therefore we cannot claim a measured retrieval gain. The scoped Domain audit newly exposed current `DEC-ADR-0004` and then both current `DEC-ADR-0004` and superseded `DEC-ADR-0003`, with their statuses preserved. Original source and adapted ADR contents stayed unchanged. The executable engineering gate passed.

## What this establishes—and what it does not

- **Established:** three possible retention dispositions can be represented without a new workflow; a pre-existing Decision corpus remains stable across the rehearsal; a single router can evolve instead of accruing duplicates; audit sources and lifecycle labels remain visible.
- **Not established:** natural-language semantic contradiction recall, long-term evidence that documentation volume stays bounded, or that a fresh AI Agent follows correct constraints in repeated real code changes. Lexical same-title/body candidate detection is an advisory heuristic, not a truth judge.
- **Remaining operational evaluation:** conduct independent, repeated real Agent maintenance tasks with pre-registered Owner-confirmed oracles. Track relevant-rule recall/precision, unrelated Decision injection, newly created durable artifact count, supersession correctness, owner re-explanations, and source-backed behavior checks. Maintain a no-PACT baseline with comparable context budget; stop on any product rule violation. Do not require this study to distort the already recorded mechanical test result.

## Implementation protections

`task finish --require-knowledge-retention` is **opt-in** to avoid breaking older Task/Convergence bundles. New `task draft` outputs a pending retention status and cannot pass as silently reviewed. A reviewed retention entry is checked for safe, changed knowledge paths; it never certifies that its rationale is true or that missing knowledge was discovered. The `audit --domain` output is bounded and explicitly reports truncation; it does not auto-delete, archive, or confirm project knowledge.
