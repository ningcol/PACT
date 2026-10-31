# Stage 2 preregistration — PACT RC1 real default vs optional Domain-first (2026-10-31)

**Status: FROZEN BEFORE ANY STAGE-2 EXECUTION OR SCORING.** This diagnostic reuses the 14 stage-1 tasks and their developer-authored oracle unchanged. It is a non-blind engineering experiment only; **no real Agent/Owner decision obedience** can be inferred.

## Immutable identity and source

- PACT under test: `v0.4.0-rc.1`, exact commit `7592efd3393ff568758400ff06d7e2e5b3315a2f`, same installed source as stage 1.
- External source: original upstream `What-We-Will/community-platform` at `52ca3e7cecab0a1568158921359cc743fdd0954a`, eight pinned upstream ADR blobs, never modified.
- Frozen 14 tasks: `7398962212a21bb00a44fb1b6750a4d96ee59868`; frozen developer oracle: `56c8c37bf841adf0b18697ab50c271f9a45fe598`. Both are imported from [Stage 1](community-platform-rc1-stage1-preregistration-2026-10-31.md) and must remain byte-identical.
- Frozen optional hypothetical Domain routes: [fixture](../../benchmarks/decision-memory/community-platform-stage2-domain-fixture-2026-10-31.json), Git blob `f1a2bb570a98bc0dbfb2285b1340d045bd8f0197`. Six developer-declared pages in disposable cloned checkout only. Domain metadata includes original source-family IDs and source-inspired titles/aliases. These **are not actual Owner-confirmed Domains**. Using `status = "confirmed"` solely exercises the existing opt-in router; do not re-label a successful routing status as real business authorization.

## Fixed test arms

1. **B-default:** original ADRs plus stage-1 source-faithful temporary PACT Decision projections, `context --risk low`, no `--limit`, `--token-budget`, `--no-code`, or `--intent` override. Actual RC1 low-risk defaults: 8 knowledge slots, 8,000 estimated tokens, default no code expansion.
2. **B-scope-no-domains:** identical workspace as B-default, only add `--scope-first`. This tests whether the flag **correctly preserves lexical Context** when the project has no genuine confirmed Domain; do not expect magic noise reduction.
3. **C-default-synthetic-domains:** add only the six tiny test-only Domain pages, same original task text, no routing flag. This is the source-matched control for C.
4. **C-scope-synthetic-domains:** same Domain-seeded workspace, same low-risk budget, add `--scope-first`. A unique route can intentionally move linked Decision sources from materialized Context to SHA-bound metadata **candidate hints**. Count these as discoverable but *not* as read/selected current Decisions.

Additional sentinel cases C2 (unique route) and M3 (shared Domain/ambiguous route) under `--risk high --no-code --scope-first`; high-risk code-disabled sentinel is explicitly **not** the full high-risk default, only a preservation check of lexical authority. Stage-1 high-budget experiment is kept as an earlier, separate reference and never substituted for default behavior.

## Measurement contract

- Preserve every per-case raw installed CLI envelope, command, return code, source SHA, selected and hinted IDs, scope status `unique/unmapped/ambiguous`, `restricted_selection`, truncation, selection budget, authority count omissions, and estimated tokens.
- Score positives strictly as **all frozen expected IDs materialized as implemented Decisions**, separately score identities only present in source-bound Domain candidate hints and weak hints, and true missing IDs. Never count hints as Agent-verified compliance.
- Score routine negatives as clean only when they materialize no current Decisions. Record additional current Decision slots but do **not** assert they are all irrelevant (0003/0009/0012 are related amendments).
- Compare B-default vs B-scope without Domain, C-default vs C-scope with developer-seeded Domain, and route validity. Do not attribute savings or improvement to the flag without a matched source baseline.
- Token estimate = fixed PACT file UTF-8 bytes / 4, **not actual usage**. Optionally compute a transparently labeled *read-all-hints counterfactual*, never a guarantee of Agent cost reduction.
- Preserve source-adapter check baseline: four original upstream `./NNNN-...` placeholder-link errors must be equal before and after projections, and any new check error fails the runner.
- No external code execution, package installation, LLM, Agent, Owner approval, release operation or upstream write. If a nonzero installed CLI, stale/forged source, undeclared Domain, truncated authority or runner failure is observed, preserve full raw receipt, do not cherry-pick positive cases.

## Decision gate

**Do not enable Domain-first by default from these developer-authored cases, even if selected Context shrinks.** The experiment is diagnostic only. Independent unseen tasks, real Agent semantic adherence, pathless/cross-Domain negative evidence, follow-up reading cost, and Owner time are outstanding. Keep #221/#214/#28/#32 open.
