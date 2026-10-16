# PACT S0–S7 current-main reconciliation — 2026-10-16

> **Status: engineering integration largely complete; original 48-AC stage acceptance is NOT complete. Release HOLD.** This is a current-main index, not a retrofit of past evidence and not a claim of real Agent/Owner benefit. All implementation changes described here are confined to `ningcol/PACT`.

## What is actually integrated into current main

The original stacked pull requests [#185](https://github.com/ningcol/PACT/pull/185)–[#193](https://github.com/ningcol/PACT/pull/193) diverged from the release-candidate mainline. **They were not merged wholesale**. Instead, the following scoped patches were rebuilt on that mainline, tested on their exact heads and merged:

| Original stage | Current-main source PR | Engineering behavior / evidence boundary |
| --- | --- | --- |
| S0 | [#209](https://github.com/ningcol/PACT/pull/209) | Frozen negative-case catalogue and blind-pilot *pre-registration*, not an original historical RED or true blind run |
| S1 | [#201](https://github.com/ningcol/PACT/pull/201) | Required medium/high passing Evidence cannot rest solely on a `workspace_changed` run |
| S2 | [#202](https://github.com/ningcol/PACT/pull/202) | Five-question Decision admission, rejected-premise evidence and full/partial supersession guidance |
| S3 | [#204](https://github.com/ningcol/PACT/pull/204), [#208](https://github.com/ningcol/PACT/pull/208) | Opt-in intent ranking, caller-required confirmed Rules, bounded README/governance navigation; legacy no-intent behavior preserved |
| S4 | [#205](https://github.com/ningcol/PACT/pull/205) | `task assist` and metadata-only `task export` without automated semantic approval |
| S5 | [#205](https://github.com/ningcol/PACT/pull/205) | Bounded untrusted `task checkpoint` and separately invocable read-only `task resume` |
| S6 | [#206](https://github.com/ningcol/PACT/pull/206) | Static `doctor --host-wiring-only` advisory, **not** execution of real Codex/Claude/OpenCode |
| S7 | [#207](https://github.com/ningcol/PACT/pull/207) | PACT-owned synthetic installed-runtime evaluation with separate frozen oracle; all human-value fields remain null |

The integrated mainline `11c311b8245361ae496d250eec14b850675fb22f` passed [PACT Check #38762219871](https://github.com/ningcol/PACT/actions/runs/38762219871) (378 tests and release-asset smoke) and [Core Matrix #38762219977](https://github.com/ningcol/PACT/actions/runs/38762219977) (9/9 reported), **but the latter report is not sufficient fail-fast evidence on Windows** because the multi-command steps previously lacked an explicit failing shell. This weakness is being fixed in [#210](https://github.com/ningcol/PACT/pull/210), which exposed previously masked Windows test failures.

Additional original-stack-to-main gap closure:

- [#210](https://github.com/ningcol/PACT/pull/210) — enforce `bash`/`set -euo pipefail` for OS matrix and Release; include new stage portability modules; run all three PACT-only synthetic cases. Windows test expectations must compare actual LICENSE source bytes and unchanged symlink targets, not host-dependent text/path spelling.
- [#211](https://github.com/ningcol/PACT/pull/211) — bounded Windows cache atomic-replace retries (WinError 5/32 only, 12 attempts), with five regression cases; merged at `8981a2bd54137831a43924b00cc496f1ba78e610`.
- [#212](https://github.com/ningcol/PACT/pull/212) — restore originally staged S0–S5 regression coverage that the first functional ports omitted, particularly stale/edited Owner acceptance, Rule/Decision Convergence, and repeat-init host preservation.

A passing Python CI run is a machine test outcome **only**. It is not owner authorization or proof that the tool reduces user effort. Do not rewrite historical SHAs, counts or actual old failed checks.

## Original 48 acceptance criteria — unchanged missing-evidence boundary

Original baseline: [historical S7 ledger](eight-stage-code-review-ledger-2026-10-15.md), which records **37/44 engineering E** with narrowly scoped evidence and **7 E missing**, plus **4/4 genuine external Agent/Owner V missing**. New integration/check runs must not automatically turn those into accepted ACs.

| Missing engineering AC | What is not yet independently substantiated |
| --- | --- |
| `AC-S0-01` | Original historic RED trigger SHAs and reproducible original failure outcomes |
| `AC-S0-04` | Independently withheld blind holdout with sealed oracle and unbiased wording |
| `AC-S2-05` | Authorized independent Agent observation preventing unnecessary durable Decision notes |
| `AC-S3-06` | Independent recall/cost non-degradation holdout |
| `AC-S3-07` | Actual comparative benefit for switching from opt-in to adopting intent retrieval |
| `AC-S7-01` | Pre-registered, genuinely blind repeated-Agent trials |
| `AC-S7-04` | Human/Agent holdout recall and overhead gates against a real control |

| Missing real-world validation AC | Missing evidence |
| --- | --- |
| `AC-S6-05` | Nine actual Codex/Claude Code/OpenCode × invocation/instruction/E2E runs |
| `AC-S7-06` | Authorized contemporary real brownfield Agent task and trace |
| `AC-S7-07` | Owner escalations, clarifications, comprehension and time, **measured rather than inferred** |
| `AC-S7-08` | Real matched-pilot semantic outcome/benefit comparison |

Owner-linked issue tracking: [#28 real pilot](https://github.com/ningcol/PACT/issues/28), [#32 effects](https://github.com/ningcol/PACT/issues/32), [#63 release](https://github.com/ningcol/PACT/issues/63). The [real Agent test matrix](agent-host-compatibility-matrix-2026-10-15.md) remains a **blocked runbook**, not an executed 9-cell Agent check.

## Gate before any tag or formal acceptance

1. Merge only the scoped hardening and coverage changes with exact-commit source review and successful full Check + **genuinely fail-fast** 9× matrix.
2. Re-run Check, 9× matrix and release-assets smoke on the **final main merge SHA**, not an older PR SHA.
3. Reconcile any new mainline changes with original #185–#193 history; close source PRs administratively only after their outstanding ACs have durable issue tracking, not by falsely marking the original eight-stage plan accepted.
4. Keep real external Agent/Owner measurements `blocked`/`null` until authorized traces exist. Formal blind A/B and claimed product benefit remain **NO-GO**.
5. Do not create `v0.4.0-rc.1` tag, GitHub Release, or `v0.4.0` stable tag on the basis of this document. Version state in current main is `.pact/VERSION = 0.4.0-rc.1`; release approval is a separate gate.

## Reproducible engineering commands

```sh
python scripts/pact/pact.py check
python -m unittest discover -s scripts/pact/tests -p 'test_*.py'
python scripts/release/release_assets.py --output-dir /tmp/pact-release-review --smoke
```

These commands verify source/test/distribution engineering only. Keep the historical [S3 fixed-input experiment](s3-installed-intent-fixed-budget-experiment-2026-10-15.md) explicitly labeled as a synthetic, non-blinded one-sample diagnostic.
