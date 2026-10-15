# PACT S0 — blinded pilot preregistration and explicit NO-GO conditions

> **Registration date:** 2026-10-15. Scope: `ningcol/PACT` only.
> Protocol preparation is an engineering deliverable, **not** an independent
> holdout, authorized real Agent session, Owner measurement, or release approval.
> The frozen development set (`benchmarks/brownfield/cases.json` and PR #184
> historical smoke) and in-repository S7 synthetic oracle are **ineligible**
> as blind test cases. Their source/answers have already been examined.

## 1. Pre-score admission and freeze

The first independently scored A/B run is **prohibited** until *all* rows
below have a concrete value, checked before opening the withheld oracle:

| Required input | Current preregistration | Gate |
| --- | --- | --- |
| Independent holdout case author/custodian | `pending`; not the assistant who implemented these tests | **NO-GO** |
| Original task wording, unmodified, per case | `pending` | **NO-GO** |
| Pinned PACT source/release SHA and independent source fixture SHA | `pending` | **NO-GO** |
| Explicit task risk level; code/doc source set; authority status | `pending` | **NO-GO** |
| Per-case knowledge/code counts, estimated-token budgets and query lists | `pending` (must match between paired arms) | **NO-GO** |
| Blind oracle path/seal/digest/custodian; no access before freeze | `pending` | **NO-GO** |
| Actual Codex/Claude Code/OpenCode runner, version and authorized isolated environment | `pending` | **NO-GO** |
| Matching runtime flags and model/temperature/seed when supported | `pending` | **NO-GO** |
| Measured admissible added token/time/tool-call tolerance | `pending`; not inferred from synthetic CI wall time | **NO-GO** |
| Real Owner pilot observer and opt-in data collection method | `pending` | **NO-GO for Owner benefit claims** |

The holdout author keeps the oracle outside the candidate/Agent's task view.
Only PACT-owned disposable fixtures are writable under current authorization.
A public historical record can be cited read-only, never rewritten or passed
off as a newly authorized external task.

## 2. Precommitted acceptance inequalities

| Signal | Frozen acceptance policy | Evidence source |
| --- | --- | --- |
| Known false `task finish` pass | **0 allowed**; any confirmed false pass is a hard FAIL | Exact negative case + Contract/Context/Claim/Owner/convergence receipts |
| Omitted explicitly required, wholly confirmed Rule | **0 allowed**; no missing required Rule may pass | Caller-specified Rule-ID and current authority |
| Candidate/pending/rejected or mixed Rule promoted to confirmed normative authority | **0 allowed** | Context Envelope + original artifact statuses |
| Relevant-file recall | **No unexplained per-case regression**: `Recall_new >= Recall_baseline`, identical target set, budgets, task, source and pre-specified queries; treat each regression as a failure until adjudicated | Withheld oracle disclosed only after predictions are frozen; count true positives and actual denominator |
| Relative precision, excess context, dropped candidates | Report per case with numerator and denominator; no fabricated aggregate win | Frozen top-k source list and oracle |
| Extra Context tokens, count, CLI operations, latency | **Acceptance limits: pending** because there is no independently matched, representative pilot control. An increase without demonstrated task correctness/recall benefit is not an accepted optimization. **Do not score the formal A/B until numeric policy is separately frozen.** | Raw paired measurements on authorized runners |
| Semantic business outcome | **Owner approval required** and cannot be inferred from machine exit 0 | Observable acceptance check reviewed by the actual Owner |
| P0/P1 trust or data-loss incident | **0 allowed**; investigation and repair before new scoring | Full incident and reproduction log |

Numeric latency/token thresholds are **deliberately unset**, not equal to
zero, and not reverse-engineered from the nine OS×Python CI micro-timings.
Even if all current PACT synthetic tests pass, that does not remove the NO-GO.

## 3. Trial design once the holdout and cost limits exist

- Use matched arms on the **same pinned source and exact task text**. Keep
  no-PACT/default-PACT/opt-in retrieval distinctions explicit. Do not call a
  synthetically installed program a real Agent session.
- For a stochastic Agent, preregister **three matched repetitions per arm**
  with identical numbered seeds where supported. Freeze configuration before
  any result; if the runner cannot reproduce seed/config, record that fact and
  a plan for matched unseeded trials **before** running. Do not claim causal
  benefit from uncontrolled single trials.
- Fix task descriptions, query expansions, risk, retrieval budgets, Agent
  prompt/instructions, versions and independent expected files before opening
  the oracle. Diagnostic post-hoc expanded queries form a **separate** set;
  they cannot repair blinded scores.
- Preserve **every** attempt: failed checks, exceptions, user interruptions,
  missing artifacts, abandoned trials and zero-result searches. Do not discard
  hard cases or silently adjust denominators.
- Redact credentials, private Owner transcripts and production data.
  Save PACT-owned event IDs, exact command/flags, version, branch SHA,
  artifact/receipt digests, wall time, file/tokens counts, false-done outcome,
  known unknowns and whether the Owner **actually observed** an improvement.
  Human metrics absent from observation remain `null/unverified`, never `0`.
- Stop scoring immediately if a known false completion, unapproved authority
  promotion, required Rule omission or P0/P1 trust violation is confirmed.
  Keep evidence for root-cause analysis and mark the experiment **FAIL/HOLD**.

## 4. Candidate outcomes and permitted decisions

**PASS is not available at this preregistration date.** Release approval
requires independent holdout availability, cost/time threshold freeze,
matched real Agent observations, real Owner-value data and successful negative
completion checks. Retrospective and fiction-only CI can keep regressing
mechanisms while the formal outcome stays `blocked`.

For optional S3 intent ranking: current engineering evidence supports the
ability to select `work/decision/history` without changing the default
CLI. It does **not** prove improved performance in a real task. The
decision for *automatic/default adoption* is **REJECT**; all opt-in behavior
remains explicitly experimental and must not be silently enabled as default.
If properly preregistered real testing finds no genuine benefit, remove or
revert the experimental ranker rather than promoting it.

## 5. Boundary and AC mapping

- **AC-S0-05 (E):** this document formally registers the no-go rule and
  known threshold/policy states *before* unseen holdout use. Pending numeric
  limits are permitted by the AC only when formal blinded A/B is **not** run.
- **AC-S0-04 / AC-S3-06 / AC-S7-01 / AC-S7-04:** **still blocked**; no independent
  withheld oracle, authoritative cost tolerance or real-runner comparison.
- **AC-S3-07:** the current rollback/default decision is documented; a
  credible benefit-based adoption of the optional experiment remains
  unverified, not an assumed user-value improvement.
- **AC-S6-05 / AC-S7-06 / AC-S7-07 / AC-S7-08:** **still blocked or unverified**;
  no real Agent×layer nine-grid or actual Owner longitudinal measurement.
- This preregistration changes neither VERSION nor code, and it does not
  authorize merging the stacked PRs or creating a `v*` release tag.
