# PACT S0 — frozen eight-stage evidence baseline (2026-10-15)

> Evidence ledger for **S0 only**. This is **not** an assertion that any later stage, real user benefit, or release is completed.
> Scope: `ningcol/PACT` only. No writes or authorization to run on `ziliu`, `zx-zsb`, `DouBaoFreeImageGen`, or other real repositories.

## Reproducibility keys and historical separation (AC-S0-01)

| Purpose | SHA | Meaning |
| --- | --- | --- |
| Owner's original eight-stage historical snapshot | `28d8a77e8bbc4fca6db320b4e1a95ac62079385b` | Historical RED evidence source; **not** a required GREEN baseline |
| Plan-frozen main | `b67d7a725774d8404ad253b43cfca3dd35874fdf` | Pre-implementation main; PR #185 plan exists separately |
| S0 implementation base | `b67d7a725774d8404ad253b43cfca3dd35874fdf` | Base of `pact/s0-eight-stage-baseline-20261015`; HEAD is the S0 PR's **actual mergeable commit** |
| Plan revision | `e8c7e138793e40060d43d3d47e1efdad2e156938` | PR #185 plan head; not an implementation/CI baseline |

For each further regression, record **original failure commit**, source fixture, invocation, expected result, and current rerun SHA separately. Do not relabel historical RED as historical GREEN.

## CI results known at freeze (AC-S0-03)

The following are **GitHub Actions completed results on the frozen *main* SHA**, not local runs on the S0 branch:

| Workflow | GitHub run ID | Commit | Result | Scope |
| --- | --- | --- | --- | --- |
| PACT Check | [38657117445](https://github.com/ningcol/PACT/actions/runs/38657117445) | `b67d7a7...` | success | Configured workflow checks, not real Owner observation |
| PACT Core Matrix | [38657117675](https://github.com/ningcol/PACT/actions/runs/38657117675) | `b67d7a7...` | success | Nine jobs: Ubuntu/macOS/Windows × Python 3.11/3.12/3.13; selected portability tests, **not** full unittest across all nine |
| PR #185 (plan-only) PACT Check | [38668161303](https://github.com/ningcol/PACT/actions/runs/38668161303) | `e8c7e13...` | success | Plan PR checks; **not** implementation acceptance |
| PR #185 (plan-only) Core Matrix | [38668161275](https://github.com/ningcol/PACT/actions/runs/38668161275) | `e8c7e13...` | success | Plan PR's selected nine-job portability suite |

Mandatory commands to rerun at each implementation head, **not** claims that they were already executed here:

```sh
python3 scripts/pact/pact.py schema-lint
python3 scripts/pact/pact.py workflow-lint
python3 scripts/pact/pact.py check
python3 -m unittest discover -s scripts/pact/tests -p 'test_*.py'
python3 scripts/pact/pact.py audit --json
```

Source, installed `pact.pyz`, installed compatibility, and the full unit-test corpus must be recorded **separately** from cross-platform portability jobs.

## Existing reproducible fixtures (AC-S0-02)

| Case | Preexisting coverage / replay entry | Baseline classification | Additional demand |
| --- | --- | --- | --- |
| Absent, renamed, or deleted Context source not silently `updated` | `scripts/pact/tests/test_convergence_deletion_semantics.py` | Covered in main at `b67d7a7` | Keep RED failure at original offending revision; rerun on S1 head |
| Rule file mixed confirmed/pending sections | `scripts/pact/tests/test_mixed_authority.py` | Existing regression | Do not represent mixed file as fully confirmed |
| Concurrent temporary files/ignored scanner | `scripts/pact/tests/test_streaming_reliability.py`, `test_discovery_ownership.py` | Existing regression | Not equivalent to an atomic source snapshot |
| Contract/context edited before finish | `scripts/pact/tests/test_task_state_atomicity.py`, `test_task_workflow.py` | Existing regression | Must remain preflight fail with no completion side effects |
| Changed-file and incomplete completion coverage | `scripts/pact/tests/test_task_change_coverage.py`, `test_trusted_completion.py` | Existing regression | Verify missing AC/coverage remains blocking |
| External verification file/source | `scripts/pact/tests/test_run_input_origins.py` | Existing regression | Not a comprehensive attestation of network/subprocess inputs |
| Rejected Decision rationale and soft-downranked history | `scripts/pact/tests/test_audit_retention.py`, `test_multi_query_retrieval.py` | Partial existing regression | Full/partial supersession, changed premises still require additional fixtures |
| Old vs new architecture competing for work Context | `benchmarks/brownfield/cases.json`, `scripts/pact/tests/test_historical_replay_metrics.py` | Historical case coverage | Dedicated holdout with blind task phrasing still required |
| Explicit requested but missing RULE-ID, nearby README, governance anchors | No full end-to-end invariant at this baseline | `unverified` (S3) | Add failing RED before implementation |
| During-run managed-worktree mutation with successful receipt | `scripts/pact/run.py` currently compares before/after hashes; `evidence.py` compares after/current | Known safety gap (S1) | RED must distinguish persistent mutation from transient write-and-restore |
| Interrupt/resume across independent sessions | Only existing task preflight and task status; no checkpoint/resume | `unverified` (S5) | PACT-owned fixture; no chat history |
| Host AGENTS/CLAUDE whitelist conflict | `scripts/pact/tests/test_bootstrap.py`, `test_distribution_upgrade.py` | Partial coverage | Safe static doctor checks (S6) |

`PR #184`'s [ziliu Evidence Smoke](real-ziliu-evidence-smoke-2026-10-15.md) is **not** a fresh blind task or a real user/Agent A/B outcome. Do not put its previous query/answer into a blind holdout.

## Frozen experiment registration (AC-S0-04/S0-05)

Tests will use a **visible task manifest** and an independently withheld **oracle**. Holdout input, fixture commit, risk, original task wording, search queries, context count, token budget, CLI/tool versions, and evaluator criteria must be fixed before any evaluated Agent sees the oracle. If a genuinely unseen case is unavailable, record `unverified` and do *not* substitute PR #184's known solutions as holdout.

Rules agreed **before** outcomes:
- **0 tolerated** known false completed claims, omitted explicit required confirmed Rules, or falsely promoted product authority.
- Do not accept an unexplained regression in relevant-file recall under identical query/risk/source/budgets. A proven relevant-file loss is a failing case pending adjudication, not an acceptable global average.
- Context count, estimated tokens, extra CLI operations and runtime overhead must be reported per-case with actual source, denominator and baseline. Features with added cost but no measured recall/correctness gain must remain opt-in or be removed.
- Source/queries/budgets fixed before oracle reveal. Late keyword tweaks are diagnostics only, not improvements in blind A/B scores.
- Repeat randomized real-Agent trials under a predeclared matched-seed/config policy when available. Record all attempts, including aborted/failed. If deterministic runner or valid pairings are unavailable, report `unverified` rather than infer causality.
- Owner clarifications, technical escalations and time are **real observational data only**; missing human metrics remain `null/unverified`.

The current in-repository `benchmarks/brownfield/cases.json` and historic smoke are a *development regression suite*, **not** the independent holdout. A new holdout must be documented and sealed before its first scored use; introducing cases after observing results invalidates its blind claim.

## External authorization/availability preflight (AC-S0-06)

| Resource | Already admissible in PACT only? | Evidence status | Unblock condition |
| --- | --- | --- | --- |
| PACT source and its GitHub Actions | Yes, same repository | Existing main CI IDs above | Capture implementation head-specific jobs |
| PACT-owned synthetic, disposable test fixtures | Yes | Authorable without touching hosts | Stage-specific tests and sealed holdout |
| Public, already sanctioned historical replay kept in PACT docs | Read-only historical facts | Partial, non-blind | Re-run with faithful frozen task/commit |
| Production `ziliu`/`zx-zsb`/`DouBaoFreeImageGen` checkout | **No** | `blocked` | Explicit permission and sanitized PACT-only duplicate; never write external repo |
| Real Codex / Claude Code / OpenCode interactive agent runners | Not proven available for these tests | `blocked` per untested cell | Valid authorized runner, version, bounded PACT fixture and audit log |
| Real Owner feedback on comparable tasks | Not provided | `unverified` | Actual voluntary observed tasks and recorded methodology |
| External API credentials, private services | **Not authorized** | `blocked` | Separate explicit authorization required; never use production secrets as fixtures |

No simulated Agent voice or fixture output can fill a live runner cell. S6/S7 real validation stays blocked while engineering E work may continue independently.

## Stage status (evidence first)

S0 is **in progress** while individual evidence rows / holdout fixture and new S0 head-specific CI execution are incomplete. Historical cases marked partial cannot be silently checked off. For each S0 item and later stage, append actual evidence in a stage Review Ledger including SHA, test/run, reviewer, RED/GREEN and unknowns. Missing real Owner/Agent resources do **not** mean the Owner workload was 0.
