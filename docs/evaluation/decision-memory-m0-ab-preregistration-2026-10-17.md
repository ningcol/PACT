# M0 decision-memory A/B pre-registration (PACT-owned synthetic only)

Date: 2026-10-17. Baseline PACT `1192363a1539ee77d5819a9cee6d9df64fb1fe17`.
All work confined to PACT and disposable local installations. This document,
input corpus and oracle must be committed **before** implementation of the
measurement runner or inspection of its results. Changes after the freeze
are separately disclosed. A/B labels are experiment arms, not Agent products.

## Core question

Does already-installed PACT locate the durable Decision needed for a new task
without prior conversation (A), and how often does **explicit caller knowledge
of the right Decision ID** allow retrieval (B)? B is a diagnostic upper bound
for a knowledgeable caller; it does **not** solve unknown-ID or autonomous
Agent retrieval. No real Agent will execute decisions in this benchmark.

## Frozen setup and differences

- Fixture: `benchmarks/decision-memory/m0-inputs.json`, fictional Markdown
  Decisions/Rules and code stubs installed only under an OS temporary directory.
- Developer-authored oracle: `benchmarks/decision-memory/m0-oracle.json`,
  stored **outside the installed project**; not an independent blind holdout.
- Same `pact.py` installed via current `scripts/pact/init.py` (compact pyz
  loader), identical task text, code disabled, low risk, `--intent work`,
  knowledge limit **4**, estimated token budget **2048**.
- A: `pact context TASK --success ... --risk low --intent work --no-code
  --limit 4 --token-budget 2048`, task text only.
- B: identical flags but `--query TASK --query DEC-ID` when the fixture
  explicitly supplies `explicit_decision_hint`. No hint = identical to A.
  The known ID appears in the *input* and is deliberately available to B,
  not recovered from the oracle. The oracle is opened only after predictions.
- The first pass additionally runs `discover` to record result IDs/status
  and historical evidence; Context is the scored boundary.

## Seven frozen cases

1. Lexically discoverable cache choice.
2. Declared code path but vocabulary disjoint: current lexical scanner may miss.
3. Pathless/lexically disjoint Decision: A may fail completely.
4. File renamed from old `paths` to new location: old anchor may go stale.
5. Partial supersession: historic constraints demand semantic review.
6. Rejected alternative: its status remains evidence, not Rule authority.
7. Unrelated task: no active Decision should be injected.

A missing Decision must never be interpreted as proof there is no constraint.
Historical Decision status is never upgraded by retrieval rank.

## Measurement and frozen engineering gates

For each arm/case store exact argv (with temporary prefixes scrubbed), selected
Context IDs, selected implemented Decision IDs, confirmed Rule IDs, discovery
candidate IDs/statuses, known-unknown count, estimated selected tokens, and
subprocess wall time. Preserve empty and failed outputs, not only successes.
The aggregate includes denominators and missed oracle IDs; never conflate
Decision recall with semantic obedience.

**Hard correctness (synthetic runner):**
- All seven cases execute on installed PACT; oracle never copied into target.
- The explicit known-ID B arm selects **100% of the six declared current IDs**
  in Context with exactly the same count and token limits.
- No non-confirmed Rule, rejected or superseded Decision is promoted into
  `applicable_rules` or current `decisions`.
- The unrelated case selects **zero current Decisions** for either arm.
- Generated authority artifacts only in the disposable installed fixture;
  no extra long-term Decisions in the PACT repository.
- Missing/stale path facts remain visible in the case-level diagnostics;
  neither B success nor M0 success claims to fix their root causes.

**Interpretation / stop gates:**
- Every A miss and false positive is retained, not tuned out.
- B's extra explicit ID is **oracle-revealing outside the actual agent**:
  compare B only on known-ID cases; do not claim causal agent benefit.
- Report B-minus-A estimated selected tokens and elapsed time *per case*,
  plus counts and denominator. Timing is diagnostic: single CI environment,
  subprocess setup cost, no frozen representative real-model ceiling.
- Do not implement C (new default graph/path scanner), Owner approval
  authentication, required Decision gates, or broad policy changes merely
  because B performs better on a privileged hint.
- **NO-GO for real independent trial claims:** independent holdout custodian,
  real Agent runner, fixed cost/time tolerance and actual Owner evidence are
  absent. Existing `docs/evaluation/s0-frozen-pilot-preregistration-2026-10-15.md`
  remains authoritative on real pilot gates.

## After running

Publish raw case-level findings and a candid GO/NO-GO decision only for
whether further *engineering experiments* are justified. Stop if A already
adequately handles the targeted cases; otherwise propose the smallest
failure-specific next test. Do not invent Agent/Owner measurements.
