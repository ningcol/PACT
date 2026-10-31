# PACT RC1 Stage 1: pre-registered no-model community-platform challenge (2026-10-31)

**Status:** FROZEN BEFORE RUNNER / NO RESULTS YET. This is a new real-source, **developer-authored/nonblind** diagnostic, **not** an independently held-out Agent study. All mutations must remain in PACT or disposable clones; never push to the upstream repository.

## Frozen inputs and identity

- Exact PACT baseline: annotated tag `v0.4.0-rc.1` -> commit `7592efd3393ff568758400ff06d7e2e5b3315a2f`. Runtime/source files must match that commit; the evaluation branch may add only benchmark fixtures, an evaluation runner, an isolated CI workflow, and documentation.
- Original, previously untested public project: [What-We-Will/community-platform](https://github.com/What-We-Will/community-platform), commit `52ca3e7cecab0a1568158921359cc743fdd0954a`, original `docs/adr/` sources **read-only**. Eight accepted project-authored ADR files are pinned by original Git blob SHA in cases.
- Task cards: [`community-platform-stage1-cases-2026-10-31.json`](../../benchmarks/decision-memory/community-platform-stage1-cases-2026-10-31.json), immutable blob `7398962212a21bb00a44fb1b6750a4d96ee59868`; 14 tasks (4 conflicts, 3 pathless no-ID, 3 partial-amendment, 4 routine negatives). No source path or ID appears in the task wording.
- Developer oracle: [`community-platform-stage1-oracle-2026-10-31.json`](../../benchmarks/decision-memory/community-platform-stage1-oracle-2026-10-31.json), immutable blob `56c8c37bf841adf0b18697ab50c271f9a45fe598`. Never inject this into installed PACT queries; score **after** all probes.
- Fixed inputs: one original task query, default intent (no `--intent`), low risk, `--no-code`, `--limit 12`, estimated token budget 45000, no additional keyword hypotheses; all cases receive identical settings.

## What the trial can establish

Two matched **engineering** readings, same public pinned source: A = minimal installed PACT with original upstream `docs/adr/` unchanged; B = same install plus **test-only** PACT-format projections of the original eight accepted ADRs (preserve original prose/status; no invented aliases, paths, rules or Owner approval). This is **not** a causal Agent A/B: B has additional project-derived metadata and original ADR copies; A does not.

Measure for each case: installed CLI return code, original Discover results, candidate Context selected current Decision IDs and source SHAs, optional deferred source-hashed hints, developer-labelled targets found/not found, false Decision injection in four routine tasks, *additional* selected Decision candidates, estimated Context tokens. An additional Decision is **not** independently confirmed irrelevant. Distinguish selected from hinted, and do not treat a hint as a passing current-Decision retrieval. Partial amendments must preserve review visibility of ADR-0003, ADR-0009 and ADR-0012 where applicable; do not pretend that amendments fully supersede earlier constraints.

The predefined strict goal: all 10 target-positive cases include every declared source ID as materialized current Decision, and 4/4 routine controls include no current Decision. Any failure must remain **NO-GO/HOLD** rather than rewriting tasks, oracle or changing runtime. Source/check/parse failures are separate engineering failures, not retrieval misses.

## Safety, ethics and limitation

- Do not run project scripts, npm or its workflows, install upstream dependencies, execute other developers' code, call external LLMs, or push to upstream; clone and read its source only.
- Verify exact upstream HEAD, allowed origin, eight Git blob hashes, tracked-clean state before/after, PACT runtime unchanged from RC1, installed compact runtime derived from exact source, and source-hash validity for selected/hinted Decisions. Preserve raw JSON with any partial failure and report it; no success by suppressing a nonzero command.
- Only semantic interpretation is a nonblind developer oracle, not independent Owner confirmation; accepted source `Status` is projected into PACT `implemented` for an experiment only.
- Original PACT issue [#221](https://github.com/ningcol/PACT/issues/221) and [#214](https://github.com/ningcol/PACT/issues/214) remain open regardless of lexical engineering performance; model/Owner behavior and actual token spend are unmeasured.
