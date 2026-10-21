# PACT no-model source-bound decision checks — 2026-10-21

**Status: engineering observations only, not a live coding-Agent A/B.**
No model was invoked, no API key provided, no real Owner decision observed, and
no repository other than PACT was written remotely. All public-source edits
were confined to ephemeral GitHub Actions working copies. The existing source
code task uses a previously authored deterministic edit; this rerun is not
independent code generation or an unseen holdout.

## Why this is worth checking

PACT's core promise is minimal durable memory, precise recall of binding
decisions and their rationale, avoidance of irrelevant Decisions, and
evidence-backed completion. A passing unit test cannot by itself demonstrate
Agent decision obedience. This report preserves what existing **no-model**
test machinery can actually observe instead of manufacturing such a claim.

## Source and scope

- Tested public project: `privacyfence/privacyfence@6a03856a6e1819b2eacd3963154ebc7d02923296`, with original upstream source read-only.
- Operative original sources: ADR 0180 (CSV spreadsheet-formula safety,
  except Grist exact round trips) and ADR 0155 (file export and data handling).
  The original ADR blobs and `src/privacyfence/export_files.py` are pinned
  in `scripts/benchmark/privacyfence_real_code_task.py`.
- The paired A/B *engineering* replay preserves identical original tracked
  source bytes, uses a single deterministic application-code patch, and
  exercises original offline tests. B alone gets source-faithful, test-only
  PACT Decision projections and the installed `pact.pyz`. Neither arm gets
  an answer-key file; no coding Agent actually makes a decision.
- Additional independent public source: `mrwilson/adr-viewer@a25f1c71e031bdaa63fe3175f969f197139f2044`, original ADRs with source-derived temporary PACT projections.

## Fresh no-model GitHub Actions observations

The links below are **2026-10-21 reruns**, not invented new unseen tasks.
Their Actions run attempts retain the original code HEAD and must not be
misrepresented as current-`main` runs.

| Existing test / rerun | Source PACT SHA | Mechanical observation |
| --- | --- | --- |
| [A/B workspace preflight, attempt 2](https://github.com/ningcol/PACT/actions/runs/39447646517) | `ee30b54f` | PASS: two identical workspaces, 971 pinned original tracked paths, no coding-Agent session |
| [Public ADR retrieval/noise, attempt 2](https://github.com/ningcol/PACT/actions/runs/39447646539) | `ee30b54f` | PASS: developer-labelled positive Decision targets 4/4, unrelated routine Decision materialization 0/8; five extraneous candidates still occurred on positive cases |
| [Real-source code edit, attempt 2](https://github.com/ningcol/PACT/actions/runs/39357514746) | `7f08941c` | PASS: exact single-file patch, pre-edit RED/post-edit GREEN, original offline suites, original Grist-specific ADR negative control, source-verified Decision retrieval |
| [ADR-viewer source adaptation, attempt 2](https://github.com/ningcol/PACT/actions/runs/39010792207) | `92f84633` | PASS: unadapted native PACT Decision-ID recall 0/4; faithfully adapted developer target recall 4/4, with 15 extraneous current Decision candidates in this historical baseline |

The real-code rerun also verified one routine test-file-only rename. PACT's
incomplete Task Evidence/Convergence correctly **blocked a false finish**,
the task created no new durable Decisions, and the initial Context selected
approximately **4,095 UTF-8-bytes/4 estimated tokens** with four source-hashed
deferred Decision hints. The estimate is **not model-billed usage** and its
near-budget size is a legitimate further efficiency question.

**Exact current-main recheck:** this report is deliberately added under the
existing `privacyfence-real-code-adr180-*.md` workflow path filter to trigger
the already-implemented, no-model, real-source Actions replay on this PR's
precise PACT code HEAD; record exact-head run status in the PR rather than
claiming success in advance. No new CI job, benchmark runner, default flag,
CLI interface, Schema, mandatory knowledge artifact or decision record is
added for this validation.

## Follow-up: lexical full-body Decision bait (2026-10-21)

A separate assistant-authored, frozen-before-fix negative source test
(`test_decision_body_noise_adversarial.py`) exposed another default
Context-noise path. The no-ID routine query `Adjust code test fixtures`
appears as generic checklist prose inside an unrelated implemented database
transaction Decision. On the **unfixed** PACT branch
[`533400f`](https://github.com/ningcol/PACT/commit/533400f390d6829ffdfdc70d00537c79752ed63b),
the direct source scorer emitted **97 points** and the two lexical labels
`body contains query` and `all query terms matched`; the original
Context incorrectly materialized that current Decision. The frozen RED
Core Matrix log has two substantive retrieval failures and one *test-only*
Context Schema misunderstanding (status is not an Envelope v1 field).

PR [#237](https://github.com/ningcol/PACT/pull/237) changes only the
Context weak-body guard: those two generic scorer labels no longer certify
applicability by themselves. The existing original-source checks for
title, exact ID/alias, long source identifier and meaningful spaced
phrase still prevent deferral; all deferred hits remain source-SHA-backed,
mandatory-to-review hints rather than silently dismissed Decisions.
Explicit `--full-decisions`, high-risk and historical lookup must remain
unchanged. Positive public PrivacyFence/ADR-viewer targets must not regress.
**Any GREEN or benefit conclusion requires actual final-head CI**; the
old developer-authored positive/negative corpus is not an independent
unseen holdout or evidence of a coding Agent obeying Decision rationale.

## What these outcomes establish — and do not

- Engineering evidence: original source pinned; Decision navigation works
  with source-faithful PACT projections on the labelled examples; selected
  routine tasks can defer irrelevant Decision bodies; an externally specified
  bad Grist change is rejected by its original source test; incomplete PACT
  completion is rejected; only disposable working copies are modified.
- Not established: independent blind relevance precision; a freshly started
  model Agent's autonomous retrieval or obedience; semantic fidelity of all
  future decisions; actual billed tokens or saved time; authenticated Owner
  comprehension, approvals or benefit.
- No success claim is inferred from a script merely exiting successfully:
  the original gates explicitly inspect RED/GREEN signatures, source hashes,
  actual JSON acceptance and failure cases. These checks remain narrower
  than an end-to-end autonomous Agent session.

**Release/real-Agent gate: HOLD.** Keep #221, #214, #28, #32 and #63 open.
No version change or GitHub Release is implied. This limited engineering
exercise honors the requirement to run **no external models**.
