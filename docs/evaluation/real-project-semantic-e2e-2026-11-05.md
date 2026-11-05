# First-stage real-project PACT E2E: ADR Viewer semantic maintenance

**2026-11-05.** Engineering evaluation only, not an independent Agent/Owner trial. This study does not redefine PACT's Product Truth, make business decisions for the upstream project, or authorize stable release.

## Reproducible sources

- **External public project:** [mrwilson/adr-viewer](https://github.com/mrwilson/adr-viewer), pinned `a25f1c71e031bdaa63fe3175f969f197139f2044`.
- **PACT implementation under evaluation:** `8b2c54e27d61ea2edb16abf6c58dd4cd6038be28` of the evaluation branch, based on existing main `ba023bd2e6a2cbf7ee6bd8d594af2088b009264d`. No PACT runtime/protocol modifications.
- **Successful exact-commit job:** [PACT Real Project Semantic Maintenance E2E #42022873953](https://github.com/ningcol/PACT/actions/runs/42022873953). The JSON output is attached as a 14-day workflow artifact, with same content logged in the Actions job.
- **Reproduction:** the branch-only workflow `.github/workflows/real-project-semantic-e2e.yml` invokes `scripts/benchmark/real_adr_decision_e2e.py` against a disposable Actions clone. Both original upstream and PACT source revisions are checked before use; installed `pact.pyz` SHA matches source-rebuilt bundle. No upstream push or PR.

The six original upstream ADRs are real source evidence. They include accepted CLI (0002), superseded coloring (0003 → 0004), amendment distinctions (0005) and accessibility concerns (0006). Their test-only PACT Decision projections preserve implementation/supersession status, but **do not claim authenticated Owner approval of the PACT projection**.

## End-to-end observed results

| Task | Real files changed in temporary upstream clone | Verification | PACT knowledge convergence | Retention |
| --- | --- | --- | --- | --- |
| Accessibility: render visible status text alongside existing icon/color | `adr_viewer/templates/index.html`, `adr_viewer/test_render.py` | New test RED then PASS, scoped and full upstream pytest; 2/2 AC; task finish PASS | 7/7 selected/referred sources | `none` |
| Ordered Status list parser semantics | `adr_viewer/parse.py`, `adr_viewer/test_parse.py` | New test RED then PASS, scoped and full upstream pytest; 2/2 AC; task finish PASS | 7/7 | `none` |
| Protect real Click CLI output against decision regressions | New `adr_viewer/test_cli_contract.py` | Real CLI integration test PASS and full upstream pytest PASS; 2/2 AC; task finish PASS | 7/7 | `none` |

Across all three sequential tasks, **6/6 acceptance criteria** have actual execution-backed Evidence and are present in Owner Reports; the total unique changed user-code/test path count is **5**. The original six source-authored Decision files remain byte-identical; PACT knowledge grew from **6 to 6**, with **zero new confirmed Product Rules** and no automatic promotion of superseded ADR 0003 as current. Git-based changed-file attribution matched the intended task deltas.

Read-only Decision discovery returned the expected source ID in all 3 tested queries (ADR 0006/0005/0002 respectively). The two broad status/accessibility queries also produced six candidates, versus one for the CLI query; this is **not a precision or token-overhead improvement result**, particularly because the tasks deliberately used `--full-decisions` and a generous context limit for completeness.

## Negative and recovery evidence

1. A genuine empty Git commit changed `HEAD` but not committed tree bytes. Both prior PACT Evidence receipts were rejected with `stale pact-run receipt`, `Git HEAD moved` and `committed Git trees are identical` explanations. Real scoped/full pytest commands were rerun after the new HEAD before completion.
2. A deliberately bad source edit removed visible status labels while preserving colors/icons. The project's new regression test **failed** as expected. PACT's static `check` returned **0** in this adverse snapshot: deterministic knowledge/schema validation does **not** automatically enforce behavioral semantics. This is a boundary of the framework, not evidence that semantic drift was accepted. The bad edit was restored before final pytest, and all tests passed.
3. The first attempt [#42022739280](https://github.com/ningcol/PACT/actions/runs/42022739280) stopped because the disposable clone had no local Git author identity for the deliberate empty commit. The isolated script was corrected to set a test-only local Git identity. This was a fixture/environment setup error, not a PACT completion bypass; the first run's failure is retained and not rewritten.

## What this proves and what it cannot

**Proven at the listed exact run:** actual external code/test maintenance executed across three PACT task lifecycles; source Decision statuses and hashes stayed intact; converged review and no-retention choices passed strict machine gates; stale evidence and regression tests rejected specific negative cases; installed PACT source identity was checked.

**Not proven:** an autonomous AI Agent correctly chooses decisions, or resists irrelevant prompt/context injection; independent project Owner approval or fewer repeated Owner explanations; statistically better retrieval precision/recall, model token savings, production accessibility compliance or real long-term knowledge stability. The task selection, code changes, semantic review text, and test oracle were written by the evaluator. No model-backed Agent or independent Owner observation occurred.

**Follow-up:** independently exercise the same project with blinded real Agent runs and owner-approved expectations before claiming behavioral compliance or real-world ROI. Keep the existing anti-false-done safeguards and treat `check` as structural, not semantic enforcement. Do not add default governance ceremonies or promote these pilot artifacts into Product Truth.
