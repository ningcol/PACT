# PACT S7 — engineering evaluation, real-pilot blockers, and release NO-GO

> **Status: ENGINEERING CHANGES UNDER REVIEW; PILOT VALIDATION BLOCKED; NO RELEASE AUTHORIZED.** This ledger is deliberately not a completion report. PACT-only modifications; no changes to other repositories. No version bump, tag, Release, external credentials or private Owner metrics.

## 1. Scope and source of evidence

The original eight-stage historical base is `28d8a77e8bbc4fca6db320b4e1a95ac62079385b`. The S0 frozen planning base is `b67d7a725774d8404ad253b43cfca3dd35874fdf`. PR #185 holds the revised execution contract `e8c7e138793e40060d43d3d47e1efdad2e156938`, on a separate unmerged plan branch.

The implementation is a stack of **PACT-only** PRs; each child PR targets its preceding feature branch:

| Stage | PR / branch | Frozen implementation head at ledger creation | Independently verifiable machine evidence |
| --- | --- | --- | --- |
| S0 | [#186](https://github.com/ningcol/PACT/pull/186) / `pact/s0-eight-stage-baseline-20261015` | `1d73759d29b655baf5ce32b8dd056ed8d5b4b5b4` | PACT Check [38668880788](https://github.com/ningcol/PACT/actions/runs/38668880788), OS×Python selected Core Matrix [38668880961](https://github.com/ningcol/PACT/actions/runs/38668880961) — success |
| S1 | [#187](https://github.com/ningcol/PACT/pull/187) / `pact/s1-evidence-trust-20261015` | `8ec7e842202fe8bdaa4ff1af72c53f4d3e4a0278` | PACT Check [38669047830](https://github.com/ningcol/PACT/actions/runs/38669047830), Matrix [38669047798](https://github.com/ningcol/PACT/actions/runs/38669047798) — success |
| S2 | [#188](https://github.com/ningcol/PACT/pull/188) / `pact/s2-decision-lifecycle-20261015` | `9d311299f1afaaad2d44df2addf0315a967ae197` | PACT Check [38669235343](https://github.com/ningcol/PACT/actions/runs/38669235343), Matrix [38669235344](https://github.com/ningcol/PACT/actions/runs/38669235344) — success |
| S3 | [#189](https://github.com/ningcol/PACT/pull/189) / `pact/s3-context-gaps-20261015` | `0972ea303e8536a702ff2074d0f78eee033bab90` | PACT Check [38669710109](https://github.com/ningcol/PACT/actions/runs/38669710109), Matrix [38669710050](https://github.com/ningcol/PACT/actions/runs/38669710050), historical Benchmark [38669710059](https://github.com/ningcol/PACT/actions/runs/38669710059) — success |
| S4 | [#190](https://github.com/ningcol/PACT/pull/190) / `pact/s4-task-assist-20261015` | `b71fa5f2aeb8de4ad081c94e6146f4353d6e5b97` | PACT Check [38670089506](https://github.com/ningcol/PACT/actions/runs/38670089506), Matrix [38670089493](https://github.com/ningcol/PACT/actions/runs/38670089493) — success |
| S5 | [#191](https://github.com/ningcol/PACT/pull/191) / `pact/s5-handoff-resume-20261015` | `470ff99bfbd4f9f700f259aaabc9e0364489a2cb` | PACT Check [38670413166](https://github.com/ningcol/PACT/actions/runs/38670413166), Matrix [38670413202](https://github.com/ningcol/PACT/actions/runs/38670413202) — success |
| S6 | [#192](https://github.com/ningcol/PACT/pull/192) / `pact/s6-host-wiring-20261015` | `480bc5e7405a0a6055856168b51ec5a9bfb09857` | PACT Check [38670763566](https://github.com/ningcol/PACT/actions/runs/38670763566), Matrix [38670763589](https://github.com/ningcol/PACT/actions/runs/38670763589) — success |
| S7 | PACT-only synthetic fixture, evaluation harness and release readiness on feature branch | **Record actual final S7 PR head after the last fix** | **Must use final-head workflow IDs**; earlier runs cannot be substituted |

These are *machine integration results*, not human correctness judgments or real Agent runs. CI's nine jobs run a **selected test subset**, not necessarily the full unit corpus in each OS×Python combination. The PACT Check has its separately documented test scope. A historical Benchmark workflow succeeding proves that the benchmark harness ran successfully, **not** that recall improved or an Owner was helped.

## 2. Two deliberately distinct regression sets

### Prior historical cases (development set, never holdout)

- `benchmarks/brownfield/cases.json`: curated historical source and target commits, task proxies reconstructed from commit messages, post-hoc manually expanded queries. Do not use these as independently blinded A/B. Do not re-fetch other repositories without lawful authorization or treat historical results as new live evidence.
- `docs/evaluation/real-ziliu-evidence-smoke-2026-10-15.md`: pre-existing Evidence Smoke, not a live owner/business change closed through a true Agent.
- Existing negative tests in PACT cover stale Evidence, mixed Rule status, changed-file omissions, convergence deletion, source-origin exceptions and non-overwriting Task drafting.

### New PACT-owned *synthetic* cases (engineering regression only)

- `benchmarks/brownfield/eight-stage-synthetic-inputs.json`: three frozen synthetic source layouts/tasks/risks/budgets.
- `benchmarks/brownfield/eight-stage-synthetic-oracle.json`: separately stored expected source paths. The harness never materializes this file in the disposable adopted project and reads it **only after** both Context modes have executed.
- `scripts/benchmark/eight_stage_synthetic.py`: PACT source installs the compact runtime into a temporary **PACT-owned synthetic** directory, invokes the real installed Context with default vs explicit `--intent work`, records files, latency, estimated tokens, unknown count and oracle-based recall/precision **proxy**; no clones, login, true Agent interaction, real Owner observation or external project write.
- `scripts/pact/tests/test_eight_stage_synthetic.py`: verifies scoring, traversal protection, installed synthetic Context execution, separate oracle and null human metrics.

Run after PR head is checked out:

```bash
python3 scripts/benchmark/eight_stage_synthetic.py
python3 scripts/pact/pact.py schema-lint
python3 scripts/pact/pact.py workflow-lint
python3 scripts/pact/pact.py check
python3 -m unittest discover -s scripts/pact/tests -p 'test_*.py'
python3 scripts/pact/pact.py audit --json
```

**Explicit limit:** these cases were designed alongside the implementation; they are **NOT** an unseen or sealed holdout. The original S0 preregistered **independent blind A/B** remains `unverified`, and S7 MUST NOT claim `Pilot Validated` from these synthetic scores. Synthetic recall costs are factual for these artificial examples only; no post-hoc Agent query improvement or generic superiority is inferred. More cases are not automatically added merely to make scores green.

### Three separate S7-E02 tracks (no cross-project writes)

| Track | PACT-side executable evidence | Observed scope | Deliberate limitation |
| --- | --- | --- | --- |
| **A — ziliu historical replay** | Existing `docs/evaluation/real-ziliu-evidence-smoke-2026-10-15.md`, `benchmarks/brownfield/cases.json`, `scripts/benchmark/historical_replay.py`; the actual GitHub historical Benchmark run linked below | Previously recorded historical source-file localization and Evidence/Task finish Smoke on a disposable old-commit copy | This is *not* a new ziliu feature implementation, present-day checkout change, or an independently blind Owner prompt |
| **B — PACT-owned fictional school-domain fixture** | `scripts/pact/tests/test_synthetic_domain_host.py`, run as part of the ordinary full suite and 3×3 selected matrix | Candidate Domain + candidate Rule are not promoted to confirmed; explicitly required candidate Rule fails, manually changed confirmed fixture is selected; nearby README is metadata-only; static host doctor does not execute host CI | This is a **fictional PACT fixture**, *not* code or Product Truth extracted from or written to `zx-zsb`; external validity is `unverified` |
| **C — PACT-owned no-chat A→B handoff** | `scripts/pact/tests/test_task_handoff.py` | Two independent Python invocations preserve prepared Task Contract/Context SHAs, recheck current Evidence/managed workspace and flag changed Decision premises; no completion inferred from notes | This proves **process-separated mechanism only**, not live Codex/Claude/OpenCode user interaction |

To interpret these: track A is retrospective, B/C are synthetic integration tests. A passing job in any of these tracks does not satisfy S6 real Agent E2E or S7 human V gates. All current fixture paths and any generated artifacts belong to PACT or disposable PACT-owned test directories, not other repositories.

### Evidence slots that must remain NULL absent observation

| Quantity | Machine-observed on a PACT synthetic run? | Human/real-Agent counterpart |
| --- | --- | --- |
| Per-case file oracle denominator, matched paths, recall, precision *proxy* | Yes, from source-file fixture scoring | Real task semantic precision and Owner success: `null/unverified` |
| Selected Context estimated tokens and number of code files | Yes, Context runtime metrics | Actual real-Agent model tokens: `null/unverified` |
| Command elapsed time for synthetic retrieval | Yes, measured in PACT Check logs | Matched real-Agent wall time and no-PACT control: `null/unverified` |
| Required Rule omissions / false completion negative cases | Test cases deliberately refuse invalid inputs | Production false-positive incidence: `null/unverified` |
| Claim/Convergence/changed-file coverage, safe partial handoff | CI test assertions and historical sample details | New authorized brownfield E2E field observation: `null/unverified` |
| Real Agent CLI operation count / Owner questions and time | No genuine real-runner task executed for these cases | All `null/unverified`; **never** zero by default |

## 3. Acceptance status by evidence category

| Metric / guarantee | Current admissible evidence | Status and what remains |
| --- | --- | --- |
| Core source/installed test behavior | Source and installed-runtime PACT regressions, final-head required | **in progress** until S7 CI passes and three reviews reconcile |
| Medium/high required Evidence bound to stable managed workspace | S1 run/evidence negative tests | **machine-regressed**; fingerprint is only before/after, not continuous file-write monitoring |
| S3 explicit Rule-ID / Context budget / hints | S3 regression, historical benchmark harness | **machine-regressed**, real-Agent retrieval benefit unproven |
| S4/S5 safe finish assistance / no-chat recovery | Real PACT-installed CLI integration tests in S4/S5 | **machine-regressed**; not portable across machines without separate state and revalidation |
| Historical source-file Recall/Precision | Pre-existing commit-diff oracle (precision is only a proxy) | **historical development regression**, no unbiased blind conclusion |
| Synthetic Context Recall/Precision and elapsed time | S7 PACT-only temporary fixture harness | **engineering diagnostic only**; cannot establish Owner benefit |
| Legitimate Agent and Owner final business judgments | No authorized recorded real Agent E2E/Owner comparison | `blocked/unverified`; **not 0** |
| Codex/Claude Code/OpenCode × CLI/instructions/E2E | Nine-cell matrix in `docs/evaluation/agent-host-compatibility-matrix-2026-10-15.md` | **9/9 blocked** (no genuine authorized runner execution recorded); not compatible-proven |
| Owner technical escalation count | `null` | `unverified` |
| Owner product decisions / clarifications | `null` | `unverified` |
| Owner additional minutes / cognitive load | `null` | `unverified` |
| Measured human/Agent overhead vs no-PACT | No matched true control | `unverified` |
| Dangerous false completed claims | Existing negative fixtures demonstrate known blocks | Strong engineering confidence; never claim all unknown failures impossible |

Acceptance states are **not** estimated percentages. One failed real negative gate fails the relevant E, and one missing V cannot be relabeled passed because its test guide exists.

## 4. Release/productization checklist — NO-GO, no tag

- The PACT source version is still `0.4.0-dev.1`; this plan has **no authority to change VERSION or publish Release**.
- A tag matching `v*` in `.github/workflows/release.yml` can **automatically trigger GitHub release asset publication**. No tag is authorized.
- Existing `scripts/release/release_assets.py` can generate `pact-bootstrap.py`, `pact.pyz`, `LICENSE` and `SHA256SUMS` with smoke verification; tag-based release workflow separately checks source/installed runtime.
- Pin third-party Actions by commit SHA; review actual `.github/workflows/core-matrix.yml` and `release.yml` at final head. Historical successful matrix cannot be substituted for a new head's matrix.
- Keep `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, project README and changelog current. Source/installed Schema compatibility and old task receipts must not be silently weakened.
- **Explicit Issue #63 Legacy YAML disposition (engineering decision: do not reintroduce `migrate`)**: Issue #63 requested a YAML deprecation/migration command during early productization. Subsequent [Issue #63 discussion](https://github.com/ningcol/PACT/issues/63) explicitly records that the YAML/profile/migrate functionality was **unreleased**, intentionally removed **before external adoption**, and had **no released users or durable persisted data requiring conversion**. The `CHANGELOG.md` records the removal. Therefore creating a legacy migration CLI today would add unsupported parser/maintenance burden, not preserve an established contract. Disposition: **historically superseded pre-release requirement**; retain TOML-only config and current install/upgrade compatibility checks. If evidence of actually released YAML users appears, reopen compatibility design with concrete input corpus and migration RED tests. **Do not close #63 yet:** after license #66 was settled and Apache-2.0 was added, its remaining issue-level gate is a separate version/tag/release-management decision. No `migrate` code or tag is authorized by this ledger.
- Do not close [#28](https://github.com/ningcol/PACT/issues/28) or [#32](https://github.com/ningcol/PACT/issues/32) until real Brownfield/Owner evidence satisfies their stated outcomes.
- A standalone independent code/plan reviewer was previously quota-blocked. Three passes by the same assistant are **not** three independent people/Agents, and cannot be labeled independent sign-off.
- Stacked PRs remain subject to review/compatibility checks and the Owner's separately approved final release scope.

**Engineering verdict:** **PARTIAL / under review**, subject to final-head CI and remaining engineering AC evidence.  
**Real-pilot verdict:** **BLOCKED** — no authorized real Agent nine-grid or human outcome data.  
**Release verdict:** **NO-GO: missing evidence + not authorized**. The release decision itself may be recorded; this does **not** satisfy missing V ACs or publish a tag.

## 5. Completion/reporting boundary

After three independent-*dimension* code reviews, append exact final commit SHAs, test commands, CI run/job IDs, defects fixed, affected regressions rerun, reviewer identity and remaining blind/real cases to a separate `eight-stage-code-review-ledger-2026-10-15.md`.

Only actual evidence can move an AC to `passed`. No synthetic Owner question counts, CI-only Agent nine-grid claims, fake agent reviews, retroactively revised RED results or unsanctioned release.
