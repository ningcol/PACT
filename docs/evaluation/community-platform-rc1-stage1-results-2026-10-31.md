# PACT v0.4.0-rc.1 Stage 1 — Real public ADR memory diagnostic (2026-10-31)

**Result: ENGINEERING PROBE PASS; strict developer-oracle RETRIEVAL NO-GO.** No Agent/Owner behavior claim. Neither PACT runtime nor upstream repository was modified. The PR stays draft pending review.

## Evidence and exact immutable sources

- PACT baseline: annotated tag `v0.4.0-rc.1`, commit `7592efd3393ff568758400ff06d7e2e5b3315a2f`. Exact parent of the PACT-only experimental branch; `git diff --quiet` verified all installed runtime, schemas, governance and project truth bytes unchanged.
- Public original: [What-We-Will/community-platform](https://github.com/What-We-Will/community-platform) at `52ca3e7cecab0a1568158921359cc743fdd0954a`. Eight accepted original source ADRs pinned to their actual upstream Git blob SHAs. All were identical after the trial; tracked upstream workspace clean, **no upstream pushes or code execution**.
- Task cases were frozen BEFORE runner code: [cards](../../benchmarks/decision-memory/community-platform-stage1-cases-2026-10-31.json) blob `7398962212a21bb00a44fb1b6750a4d96ee59868`. [Developer oracle](../../benchmarks/decision-memory/community-platform-stage1-oracle-2026-10-31.json) blob `56c8c37bf841adf0b18697ab50c271f9a45fe598`. Git captures original append-only commits and source identifiers.
- Completed **exact-run-head** probe: [GitHub Actions run 41162361123](https://github.com/ningcol/PACT/actions/runs/41162361123), head `14d094d2612c666c45de5c84c99749f29b45a9d3`. [Full raw JSON artifact](https://github.com/ningcol/PACT/actions/runs/41162361123/artifacts/13027567660) preserves A, B, selected/hinted sources, full CLI payloads, scores and failures. Matched upstream clone, installed runtime built and byte-verified against the exact PACT source.
- Initial preserved failed run: [41162245798](https://github.com/ningcol/PACT/actions/runs/41162245798), [raw failed receipt](https://github.com/ningcol/PACT/actions/runs/41162245798/artifacts/13027137885). The original upstream ADR README/template contain four literal `./NNNN-...` placeholder links. Original PACT `check` reports four broken-example links **both before and after** the eight source-faithful PACT projections. No changes were made to upstream sources or PACT's checker; runner was amended to compare exact baseline and final errors rather than suppress them. Added errors: **0**. This does **not** mean the full installed `pact check` returned exit zero: it returned 1 on these upstream placeholders.

## Trial definition

A = source project with its original `docs/adr/` plus a minimal temporary PACT install, no PACT-format Decision projections. B = same original source, same installed PACT, plus eight test-only Decision projections with original prose/status and rebased relative Markdown links. These metadata copies are **not authenticated Owner approvals**, and this A/B is not a controlled model-benefit study.

All 14 new developer-authored tasks used one original no-ID/no-path query, default intent (no `--intent`), low risk, `--no-code`, explicit high diagnostic ceilings of `--limit 12` and `--token-budget 45000`. These intentionally generous ceilings are **not standard PACT defaults**, and results under them must not be generalized to all everyday default-context runs. The same settings were applied across all tasks and both phases. The oracle was not passed into PACT and was scored only after all raw probes completed.

The four categories were predeclared: four direct Decision-conflict tasks (C), three pathless/no-ID behavior queries (P), three partial-amendment conflicts (M), and four routine-no-decision controls (N). All positive expected Decisions must be **materialized as current**, not merely appear in a hint, to count as a hit. Extra oracle-unlisted Decisions are not independently judged semantically irrelevant.

## Observed score summary

| Measure | Observed | Strict interpretation |
| --- | ---: | --- |
| B positive cases with every target selected | **10/10** | Developer-labelled source recall in this fixed corpus |
| B individual target source occurrences selected | **14/14** | None were hint-only or wholly missing |
| B routine negatives without selected Decision | **1/4** | **3/4** had irrelevant-to-task selected Decision(s) under the frozen developer labels |
| B extra current Decision selection slots outside oracle | **7** | Four lie in the actual related supply-chain amendment family; do **not** call all seven irrelevant |
| A original ADR target document-source paths present | **14/14** | A also found the target original documents; B is **not evidence of better source recall** |
| A original ADR materialization slots, all tasks | 141 | Includes raw documents in routine tasks; wide count budget |
| B original ADR document slots + PACT typed Decision slots | 121 + 21 | Duplication and extra reads are possible |
| A aggregate CLI estimated Context tokens | 478,775 | file UTF-8 bytes / 4 estimate, not model usage |
| B aggregate CLI estimated Context tokens | 497,241 | +18,466 / +3.86% vs A, *not causal billed-model overhead* |
| Mechanical authority-count omissions | 0 | All 14 B contexts recorded 0 dropped authoritative candidates |
| Original upstream tracked files modified | 0 | Source blobs equal, clean tracked Git workspace |
| New PACT check errors from source projections | 0 | Four original placeholder links remain flagged before/after |
| Real coding Agent, independent oracle, Owner evaluation | **none** | No Decision adherence or human benefit measured |

### Per-case selected Decision sources (B only)

| Case | Developer expected IDs | Materialized current Decision IDs | Interpretation |
| --- | --- | --- | --- |
| C1 | 0003 | 0003, 0012, 0009 | target found; additional two are related amendments |
| C2 | 0011 | 0011 | target found |
| C3 | 0006 | 0006 | target found |
| C4 | 0007 | 0007 | target found |
| P1 | 0004 | 0004 | no-path target found |
| P2 | 0007 | 0007 | no-path target found |
| P3 | 0014 | 0014 | no-path target found |
| M1 | 0003, 0009, 0012 | 0012, 0009, 0003 | full partial-amendment family located |
| M2 | 0009, 0012 | 0012, 0003, 0009 | target found; related earlier source also surfaced |
| M3 | 0003, 0012 | 0003, 0012, 0009 | target found; related intermediate source also surfaced |
| N1 | none | **0003** | unwanted security-gate Decision in typo-only task |
| N2 | none | none | clean import-order task |
| N3 | none | **0009** | unwanted waiver Decision in local test-fixture rename |
| N4 | none | **0004** | unwanted URL-routing Decision in README-whitespace task |

All IDs in the table are suffixed forms of `DEC-CPL-NNNN`. These are experiment-assigned identifiers derived from original numbered ADRs; none appeared in task prompts.

The installed Discover ranking for all three routine false positives used generic lexical scores with empty reported reason lists, not an exact source ID or a verified task scope. N1 selected 0003 with score 54, N3 selected 0009 with score 24, and N4 selected 0004 with score 24. The current source makes these plausible weak/full-body matches, but this experiment **has not** independently isolated a unique causal term for each; do not implement a new default threshold from these fourteen informed examples.

## Review of validity and limitations

1. **Source integrity:** exact PACT and upstream commit/blob pins pass; PACT runtime unchanged; test-only source projections are anchored to genuine accepted upstream ADR text with no invented aliases, paths, Domain truth or Owner authorization. CLI outputs preserve SHA-backed selected and deferred sources.
2. **Pre-registration:** 14 case strings + oracle hashes precede the runner commits. The scorer has no ability to rewrite them. Nevertheless the *same assistant* selected source material, authored the cases, judged the oracle and reviewed results, so independence/blinding is **absent**.
3. **Adversarial controls:** positive/partial/negative cases were not selected after looking at output, and both first failing and second successful engineering runs are retained. No test failures were erased; no PACT source changes were made.
4. **Readiness:** an experimental check step's success means evidence was collected safely, not that semantic retrieval passed. The strict frozen success goal is **NO-GO** due to 3/4 routine injections. Raw original ADR retrieval under wide budgets already reached 14/14, so no incremental PACT recall claim is supported.
5. **Scope of evidence:** no fresh coding-Agent session, actual semantic obedience, independent blind holdout, measured Owner comprehension, billable token consumption, upstream CI or production effect. Leave [#221](https://github.com/ningcol/PACT/issues/221), [#214](https://github.com/ningcol/PACT/issues/214), [#28](https://github.com/ningcol/PACT/issues/28) and [#32](https://github.com/ningcol/PACT/issues/32) open.

## Stage 1 decision and handoff

**Stage 1 test completed as a no-model engineering diagnostic; reliability target remains HOLD.** No runtime change is justified from the developer-labelled results alone. PACT correctly supplied all predeclared targeted durable rationale in this corpus, including cross-record amendment chains, but still materialized unwanted Decisions in routine tasks with deliberately wide ceilings. Raw ADR documents alone also supplied the full target corpus at this budget. Do not turn `--scope-first`, a smaller reading limit or another filter into the default from these observations.

For a separate Stage 2, evaluate present default count/token ceilings plus opt-in routing against frozen/independent source tasks, emphasizing **materialized authority recall vs routine source overhead** and preserving partial-amendment/rejected-history safety. Keep any semantic or model/Owner superiority claims explicitly unverified until an authorized real-agent trial exists.
