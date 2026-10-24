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

## Source-first audit of remaining candidate cost (2026-10-21)

Follow-up to [Issue #221](https://github.com/ningcol/PACT/issues/221).
The verified no-model [PrivacyFence run](https://github.com/ningcol/PACT/actions/runs/39598827008)
at PACT `d3c2d183` retained **10/10 developer-labelled target Decisions**,
with **10 additional source-authenticated current-Decision selections** and
**0/2 routine current-Decision injections**. Reading the case-by-case
`selected[]` receipts gives **21,599 estimated tokens** (UTF-8 bytes / 4)
across those 10 additional selections: **39.7% of B's 54,422 selected
estimated tokens**. Two additional selections of ADR 0008 alone contribute
**10,344** estimated tokens (2 × 5,172). The source-A estimate was 43,640;
the B–A initial Context difference was +10,782 (+24.7%), **not** provider
billing, incremental Agent context usage or a provable savings opportunity.
Some additional selections may be necessary safety context.

Recorded extra-current selections by frozen case (developer-oracle-relative,
**not confirmed irrelevant**):

| Source / task | Extra Decision IDs (selected, not merely hinted) | CLI estimated tokens |
| --- | --- | ---: |
| PrivacyFence / `mcp-signin` | 0008, 0014 | 6,665 |
| PrivacyFence / `route-gating` | 0195 | 1,065 |
| PrivacyFence / `legacy-settings` | 0014, 0195 | 2,558 |
| PrivacyFence / `csv-formulas` | 0191 | 1,310 |
| PrivacyFence / `salesforce-batch` | 0013 | 1,520 |
| PrivacyFence / `personal-import` | 0008, 0014 | 6,665 |
| PrivacyFence / `signed-serial` | 0041 | 1,816 |
| adr-viewer / `uniform-status-headers` | 0005 | not independently cost-adjudicated |
| adr-viewer / `amendment-as-supersession` | 0001 | not independently cost-adjudicated |
| adr-viewer / `remove-screen-reader` | 0001, 0004, 0005 | not independently cost-adjudicated |

The first seven rows total 10 extra PrivacyFence slots and 21,599
estimated tokens. The last three total five additional adr-viewer
slots. All other frozen cases selected no developer-oracle-extra
current Decision. Counts retain their original frozen task denominator.

Representative original-source findings:

- PrivacyFence [ADR 0008](https://github.com/privacyfence/privacyfence/blob/6a03856a6e1819b2eacd3963154ebc7d02923296/docs/adr/0008-one-principal-per-os-user.md)
  governs OS-user isolation and MCP tokens; its status explicitly says
  *implemented in part*. It is not automatically irrelevant to login or
  personal-settings changes merely because the developer oracle named another
  primary target.
- PrivacyFence [ADR 0014](https://github.com/privacyfence/privacyfence/blob/6a03856a6e1819b2eacd3963154ebc7d02923296/docs/adr/0014-every-bespoke-route-is-classified-or-the-app-refuses-to-start.md)
  explicitly links original ADR 0013 and addresses settings POST approval
  gates; cross-task selections can be real authority to inspect, not junk.
- adr-viewer [ADR 0005](https://github.com/mrwilson/adr-viewer/blob/a25f1c71e031bdaa63fe3175f969f197139f2044/doc/adr/0005-distinguish-amendments-to-records-with-colour.md)
  explicitly **amends** [ADR 0004](https://github.com/mrwilson/adr-viewer/blob/a25f1c71e031bdaa63fe3175f969f197139f2044/doc/adr/0004-distinguish-superseded-records-with-colour.md);
  its appearance on a status-colour task cannot safely be called a proven
  false positive. The original accessibility ADR 0006 is also related to
  interpreting records without relying solely on colour.

**Decision:** no automatic default ranking/filter or mandatory note is
introduced from these developer-oracle extras. Existing source-bound
`selected[]` receipts already contain ID, SHA and estimated file cost.
The existing PrivacyFence engineering scorer now adds an **advisory,
source-verified accounting field** for the same 10 extra slots and their
estimated selected bytes/4. A malformed, missing or duplicate extra-source
receipt fails the cost attribution instead of quietly manufacturing a lower
estimate. This is cost *attribution*, not a semantic relevance verdict or
predicted money/token savings. The frozen cases and oracle are unchanged.
Only actual exact-PR-head GitHub runs can confirm the emitted field.

## 2026-10-23 proposed no-model downstream staged-source-read experiment

**Study status: developer-informed, unblinded engineering diagnostic, NOT Agent
efficiency evidence.** No upstream/code/Decision/oracle modifications, new
default behavior or external model. Both pinned public repositories retain
their pre-existing, developer-authored task text and source-hashed answers:
PrivacyFence `6a03856a6e1819b2eacd3963154ebc7d02923296` (10 positives,
2 routine negatives); adr-viewer
`a25f1c71e031bdaa63fe3175f969f197139f2044` (4 positives,
8 routine negatives). The developer has already inspected earlier scores and
several selected-source orders. The study is **not a new blinded holdout**.

Before opening a case's developer oracle, an instrument operating on the
**installed PACT Context Envelope** records the ranked list of current
Decision source IDs, paths and SHA-256, then physically reads the complete
file bytes in a source-hash-verified local copy. The **full** counterfactual
exposes all selected current Decision bodies; the **first-only** counterfactual
exposes just the earliest selected current Decision source, while retaining
the metadata for the other candidates. Neither treatment modifies what PACT
selects, Convergence obligations, or the original project source. The
instrument also records source bytes and the same bytes/4 estimator used by
PACT. It does not measure internal index/discovery I/O, a model context window,
elapsed coding-Agent time, actual provider tokens, or real Owner attention.
Reading all bytes to verify each candidate is **measurement instrumentation**,
not a claim that first-only used less physical test-runner I/O.

Only **after** candidate order and source hashes are fixed may the frozen
developer oracle be used to score how many original *primary* targets were
present in first-only versus all-selected. The two routine negatives must
select zero current Decisions. **Stop rule:** any first-only target miss,
source/hash/identity failure, historical-as-current promotion, new routine
injection or lost original all-selected positive is an immediate **NO-GO for
default first-only**, regardless of estimated downstream byte reduction.
Even if first-only finds every developer-labelled primary, safety still needs
independent evaluation of cross-domain constraints, partial supersession,
semantic obedience and Owner impact; therefore no default rollout is
authorized by these no-model trials. Existing `--full-decisions` and
Task Convergence must remain available/mandatory where applicable.

## 2026-10-23 measured staged-reading outcome — exact source-rebuilt PACT

The frozen no-model protocol above was executed on installed PACT commit
`6b860e5494515e705d73f56d33a186de2d72dc30`, using byte-for-byte
verified original public source files and original developer-authored
task/oracle hashes. Source order was recorded before consulting oracle.
The experiment physically read **all** selected source files for SHA-256
verification; these figures represent *counterfactual downstream exposure*
under different read policies, not reduced CI I/O or observed model tokens.

| Public pinned source | Original selected primary targets found, all-current | First-current-only primary targets found | All-current Decision full-source bytes | First-current-only full-source bytes | Bytes not exposed under first-only |
| --- | ---: | ---: | ---: | ---: | ---: |
| [PrivacyFence run](https://github.com/ningcol/PACT/actions/runs/39912371648) | **10/10** | **10/10** | 152,662 | 66,278 | 86,384 (56.6%) |
| [adr-viewer run](https://github.com/ningcol/PACT/actions/runs/39912371557) | **4/4** | **2/4** | 9,783 | 4,089 | 5,694 (58.2%) |

For PrivacyFence, the selected-current Decision bytes/4 estimates were
38,172 versus 16,573. The two routine negative tasks selected no current
Decisions, and source-verified positive recall was unchanged.
For adr-viewer, estimates were 2,448 versus 1,023, with eight routine
negatives selecting no current Decisions. On the positive
`amendment-as-supersession` case the first source was `DEC-ADR-0001`,
while the primary target `DEC-ADR-0005` was also selected but not first.
On `remove-screen-reader`, the first was `DEC-ADR-0001`, whereas
`DEC-ADR-0006` was the original primary accessibility target.
Both are actual **primary Decision misses under first-only**, independently
of any judgement about cross-domain obligations in the other selected records.

**Conclusion: first-current-only as a PACT default is NO-GO.** A higher
estimated byte reduction cannot compensate for losing preserved decisions.
The first-only policy was never enabled in runtime; existing `discover`,
`context`, bounded source-hash hints, explicit history/full source lookup and
Task Convergence remain unchanged. Metadata-first navigation followed by
selective, **adequately complete** source reading remains available through
existing interfaces, but this study does not establish any general
downstream read policy as semantically sufficient. No new Decision summary
files, LLM requests, default command, schema or Agent/Owner approval workflow
were added. Frozen M0 benchmark code retains its original Git blob after an
initial experiment-isolation failure was corrected. New experiment code
lives in benchmark-only support, not the installed runtime.

The pre-final attempt [PACT Check run](https://github.com/ningcol/PACT/actions/runs/39910996718)
failed because newly added instrumentation modified the frozen M0 fixture
builder, **not** because a PACT installed runtime behavior regressed;
the M0 source was restored byte-for-byte. An intermediate PrivacyFence run
also failed on an experiment-local Python module name shadowing error, fixed
without changing public tasks or answer key. The final experiment SHA's
PACT Check had **619/619** passing tests and
[real-source code E2E](https://github.com/ningcol/PACT/actions/runs/39912371519)
passed. Final merge eligibility still requires exact-head CI and review;
no claim of merge or main CI is made by this research paragraph.

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
