# Stage 2 — PACT RC1 actual low-risk defaults vs optional Domain-first on pinned public ADRs

**Date:** 2026-10-31. **Engineering collection: PASS; Domain-first DEFAULT ADOPTION: NO-GO.** This is a nonblind, author-labelled, no-model **retrieval mechanism diagnostic**, not an Agent decision-obedience experiment.

## Immutable evidence, exact identity

- PACT runtime: `v0.4.0-rc.1` tag resolving to `7592efd3393ff568758400ff06d7e2e5b3315a2f`. Evaluation HEAD `4599ec08210b32aeb43da8e7541e1d4c413cdce6` only adds PACT-owned benchmark, fixture, CI, and preregistration files. The installed `pact.pyz` byte-for-byte matches the runtime rebuilt from this source; no RC1 runtime/schema/default behavior changed.
- External real read-only source: [What-We-Will/community-platform](https://github.com/What-We-Will/community-platform) at `52ca3e7cecab0a1568158921359cc743fdd0954a`. All eight original accepted ADR Git blobs verified before/after; tracked upstream Git clean; no project scripts, npm, external models or upstream writes.
- Same frozen 14 Stage-1 cases `7398962212a21bb00a44fb1b6750a4d96ee59868` and developer oracle `56c8c37bf841adf0b18697ab50c271f9a45fe598`, unchanged.
- Six **developer-hypothesized** Domain routing pages frozen before Stage-2 runner code, original fixture Git blob `f1a2bb570a98bc0dbfb2285b1340d045bd8f0197`. These temporary pages use PACT `status = "confirmed"` **only to activate the test router**. The public project Owner did NOT confirm them. Aliases were designed with knowledge of Stage-1 tasks and therefore cannot be treated as independent routing evidence.
- Exact successful [GitHub Actions run 41167153162](https://github.com/ningcol/PACT/actions/runs/41167153162), source HEAD `4599ec08`, [full raw 58-case/context CLI JSON artifact](https://github.com/ningcol/PACT/actions/runs/41167153162/artifacts/13029314863). Raw receipts include all low-risk cases in four paired arms plus two high-risk/no-code sentinels. A green workflow confirms mechanical source integrity and receipt collection, **not** the semantic/recall GO.
- Original upstream ADR README/template include **four** `./NNNN-...` placeholder-link `pact check` errors before and after PACT experimental adaptation. Zero additional errors were introduced, but this does **not** mean the full adapted project's `pact check` returned zero.

## Matched comparison and actual default budgets

All low-risk arms invoked `pact context "<unchanged frozen task>" --success "<identical test success>" --risk low` with no `--limit`, `--token-budget`, `--code`, `--no-code`, `--intent`, `--query`, or `--full-decisions` override. RC1 low-risk policy provides **8 selected knowledge artifact slots**, soft **8,000 estimated tokens** and code discovery off. Security/decision source authority can legitimately exceed the soft budget and records overage. Every task used the same source-original ADRs and exact stage-1 projections.

- **B-default:** projected Decisions, no Domain files, no `--scope-first`.
- **B-scope-no-domains:** identical source, `--scope-first` added, no confirmed Domain.
- **C-default-synthetic-domains:** same source plus exactly six small developer-invented Domain pages, no `--scope-first`.
- **C-scope-synthetic-domains:** same Domain-seeded source as C-default, `--scope-first` added.

Crucial: A `scope_route.candidates[]` entry or weak Decision hint is a SHA-bound **navigation pointer**, not a materialized file read, semantic applicability finding, or authorized Owner decision. We score it separately; a task does not pass the strict materialized-Decision target merely because it received a hint.

## Aggregate observed results

| Metric across 14 unchanged tasks | B default/no Domain | B scope/no Domain | C default/test Domain | C scope/test Domain |
| --- | ---: | ---: | ---: | ---: |
| Positive tasks with **all targets materialized** | 10/10 | 10/10 | 10/10 | **3/10** |
| Expected Decision occurrences materialized | 14/14 | 14/14 | 14/14 | **6/14** |
| Expected Decision occurrences only SHA-bound hints | 0 | 0 | 0 | **8/14** |
| Expected Decision IDs absent from materialized AND source-bound hints | 0 | 0 | 0 | 0 |
| Routine negatives with ≥1 selected current Decision | **3/4** | **4/4** | **3/4** | **4/4** |
| Developer-oracle extra current Decision slots | 7 | **90** | 7 | **45** |
| Sum of initial selected Context estimated tokens | 108,782 | **286,821** | 107,256 | **141,491** |
| Weak Decision hint truncation (needs explicit broader review to finish) | **9/14** | 0 | **9/14** | 0 |
| Known authoritative candidates omitted by hard count | 0 | 0 | 0 | 0 |
| Scope statuses unique / unmapped / ambiguous | — | 0 / 14 / 0 | — | **7 / 6 / 1** |
| Scope restricted-selection actually enabled | — | 0 | — | 7 |

**B scope-no-domain actually increases initial selected estimated tokens by +178,039 (+163.7%) versus B default.** Even the supposedly harmless `unmapped` branch changed all 14 selected Decision lists: B-default's weak Decision deferral was lost and authority overage materialized many source files. In B-scope, 14/14 low-risk cases exceeded the soft budget while preserving current implemented Decisions as mandatory authority; do **not** mistake the 8,000-token policy for a hard guarantee. This is a **mechanically confirmed default-fallback behavior regression** relative to the documented expectation of retaining baseline lexical Context. It does NOT demonstrate Agent misuse.

**C scope with test Domains increases** initial selected Context estimated tokens by **34,235 (+31.9%)** over the matched C default. Seven uniquely routed tasks materialize only tiny Domain pages (approx. 93–118 estimated tokens each), but their expected source Decisions are **metadata hints** only, not read. The sum of *additional source material if every displayed scoped hint were read* is approximately **35,786 estimated tokens** beyond the initial 141,491, a counterfactual not observed reading/cost. Thus a small initial unique-domain packet is not proven cheaper once its deferred source reviews are counted.

There is no independent holdout, actual token billing, model API, coding Agent, Owner observer, or statistically defensible real-world improvement estimate. All numbers are file-size UTF-8-bytes/4 estimates aggregated over **14 separate tasks**, not tokens consumed in one request.

## Per-case coverage and safety

**Actual default B:** 14/14 frozen target Decision occurrences selected. Four routine negatives: N1 selected unrelated `DEC-CPL-0003`, N2 clean, N3 selected `DEC-CPL-0009`, N4 selected `DEC-CPL-0004`. The 7 additional selected Decision slots outside developer oracle include four true source-connected 0003/0009/0012 amendments and cannot all be declared irrelevant.

**Scope with no Domains B:** 14/14 tasks are `unmapped`; none restricted. All four routine controls materialize current Decisions, with N2 now including all eight projected current Decisions. This is not a Domain matching problem; RC1 code bypasses the ordinary weak-body deferral when `args.scope_first` is true.

**Scope with test Domains C:** C1/C2/C3/C4/P1/P3/M2 have single Domain matches and no materialized current Decisions; related source Decisions are in metadata candidates (8 expected target occurrences) and require deliberate reading/convergence review. P2 and M1 have no matching Domain and preserve their expected Decision IDs via broad fallback. M3 matches two Domains and retains its expected 0003/0012 Decisions via broad fallback, demonstrating the *ambiguity safety guard*. N1–N4 have no Domain mapping and all materialize one or more unrelated Decisions. Developer-authored routers therefore did not solve routine noise. Even a matched high-risk/no-code sentinel for C2 and ambiguous M3 kept `restricted_selection=false` and all predeclared target Decisions selected, but the `--no-code` override means this is **not a full high-risk default E2E**.

**No missing source identity:** selected and hinted Decision IDs/paths/SHA256 all match the experimental source projections; Domain hints are never promoted to Owner-confirmed Product Rule or semantic applicability, and scope `applicability_verified` remains false. Original project tracked content is unchanged.

## Diagnosed cause from exact RC1 implementation (not guesswork)

[RC1 Context implementation](https://github.com/ningcol/PACT/blob/7592efd3393ff568758400ff06d7e2e5b3315a2f/scripts/pact/context.py) deliberately allows unique `scope_route.status` to restrict selection only on unique, non-high-risk/normal-work routes and conservatively preserves candidates on `unmapped` / `ambiguous`. **However**, after route handling, the ordinary weak-Decision deferral branch has an unconditional `and not args.scope_first` precondition. Therefore a flag that routes to **nothing** still turns off the default weak-Decision deferral and changes selected Context. This accounts for the observed B fallback amplification and violates the intended “no Domain = preserve baseline Context” user expectation.

This diagnosis is limited to the exactly pinned RC1 revision; no runtime or ranking fix was performed in Stage 2. Do **not** turn `--scope-first` on by default, lower safety thresholds blindly, declare hinted Decisions already obeyed, or delete historical amendments.

## Follow-up, bounded to the already-open #221

Recommend a narrow Stage 3 correction/test **only after formal review**: when `--scope-first` is requested but **not actually restricting selection** (`unmapped`, `ambiguous`, high-risk and any overflow fallback), preserve normal low/medium single-query weak-Decision deferral wherever that default would otherwise apply. Preserve explicit `--full-decisions`, history, high-risk, necessary cross-domain decisions, source-bound hint/Convergence fail-closed semantics. Add direct default-vs-unmapped/ambiguous parity regression and a real pinned-source check; consider separate safety tests for source-changing race and partial amendments. Do not introduce a new default flag or new Domain requirements.

Also note the separate **Stage-1 final PR** Windows Core Matrix run [41162655040](https://github.com/ningcol/PACT/actions/runs/41162655040) had a timeout subprocess-survival test failure in `test_task_workflow`; Stage-2 retrieval smoke success is not a substitute for full matrix green, and the existing timeout test was not modified by these evaluation-only files.

**Stage 2 conclusion:** The original default performed better on noise/cost in this frozen set. Default Domain-first promotion is **NO-GO**. Existing #221/#214/#28/#32 remain open; neither source-study nor opt-in Domain route proves actual Agent/Owner benefit.
