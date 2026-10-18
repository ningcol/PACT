# Decision-memory real-Agent cold-start A/B — execution gate and handoff

Registered **2026-10-18**; **PACT only**. Exact engineering baseline `82c8975f6678d77c7ee0f9ef31755553488325e7` (merged PRs #219/#220); real *read-only* source [mrwilson/adr-viewer](https://github.com/mrwilson/adr-viewer) at `a25f1c71e031bdaa63fe3175f969f197139f2044` (six existing ADRs).

**Status: BLOCKED / NOT RUN.** The current connected tooling performs GitHub retrieval, workflow checks, and Codex **PR review**, not a credentialed, authorized fresh Codex/Claude Code/OpenCode coding session. PR-review comments, installed `pact.pyz` probes, developer-authored M0/M1 task cards, and GitHub Actions Python tests **must never be counted** as real Agent decision obedience. No verified independent holdout author or authenticated Owner observer has been supplied. Do not put fake Agent receipts or unsealed answer keys in this repository.

## 1. Admissions — stop unless every prerequisite is proven

| Gate | Required evidence | Current |
| --- | --- | --- |
| Baseline | Exact PACT main commit above, external repo original commit and six ADR blob hashes pinned by #220 | Verified engineering source |
| Independent task/answer custodian | Not the PACT implementer or evaluator author; new untouched tasks with task text frozen before any Agent attempts | **Pending** |
| Sealed oracle | Stored **outside** both Agent workspaces and PR; digest/custodian and custody transition recorded | **Pending** |
| Real, isolated Agent runner | Name, mode, model/version, clean per-run session, authenticated runner access, complete JSONL/transcript with command provenance | **Pending** |
| Same paired experiment | Both arms use identical task wording, source/commit, time cap, tool rights and model settings; only the PACT intervention differs | **Pending** |
| Financial and process stop limits | Numeric per-session/aggregate cost, token and time limits frozen *before* attempts; no unbounded agent run | **Pending** |
| Owner observation | Actual Owner decision changes/escalations/understanding measured with opt-in; absent values recorded as `null` | **Pending** |

**Fail closed**: if any required admission cannot be authenticated, do **not** launch the formal blinded comparison, score a proxy, or mark a Release gate passed. See existing [S0 protocol](s0-frozen-pilot-preregistration-2026-10-15.md) and unresolved [#214](https://github.com/ningcol/PACT/issues/214).

## 2. Study shape (preregister before unsealing)

- An **independent** custodian creates at least **12 new tasks** in the pinned source; historical/development test cards in #218–#220 are barred. Include decision conflicts, partial amendment, superseded rationale, code relocation, pathless vocabulary, and routine negative controls. Freeze task hashes, oracle digest, per-case risk and scoring rubrics *before* any Agent sees the task.
- Compare **A: direct original ADRs, no PACT Decision routing** with **B: original ADRs plus PACT installed and minimal source-faithful Decision projections**. For each independent task use the same clean pinned source and identical permitted code/test access. B's extra source-derived metadata is the explicit treatment—not an invisible scoring hint.
- Run **three independent clean sessions per task per arm**, randomizing paired ordering; target 12 × 2 × 3 = **72 real coding sessions**, only *after* credible cost ceilings and authorization are fixed. If fewer runs are authorized, label them **non-confirmatory pilot**, never the predeclared formal study.
- Each Agent must **attempt the actual coding task** in an ephemeral clone, not merely print Context. Preserve original ADRs byte-for-byte; prohibit pushes, tags, external PR/Issue mutations, exfiltration, production access and modifications of the PACT evaluator. **No Decision IDs, source paths, scoring rubrics or oracle entries** in Agent prompt except what the Agent itself finds. Do not let the PACT scorer run inside the Agent's writable workspace.
- Isolate each arm and repetition from all prior agent history, sessions, tool caches and the other arm's diff. Separate trusted scorer process/judges from untrusted Agent execution. A code-test pass by itself is **not** a semantic Decision-obedience pass.

## 3. Per-session evidence (save even on failures)

Record: fixture SHA, baseline PACT SHA; case/task digest; arm/run index; Agent CLI/version/model/config/permissions; complete unredacted-to-custodian but credential-sanitized external transcript/JSONL; actual commands and tool result statuses; original and final worktree hashes plus unified diff; selected Decision IDs **with source path and rationale**, including superseded/partial clauses; pass/fail of relevant code tests; whether Agent requested approval *before* changing an Owner decision; false-done claims; long-lived Decisions created (including unwanted routine notes); provider-reported model tokens, actual wall time and tool calls; Owner interventions/clarification counts and minutes. Missing human data = `null/unverified`, never zero. The human auditor can supply an independent score only after all predictions and diffs are frozen.

## 4. No-go and product consequences

- **0 tolerated**: proven silent unauthorized supersession, false-done, historical/rejected authority promoted to current, P0/P1 trust incident, or evidence fabrication.
- A false-positive irrelevant Decision may block useful work even when correct source was also selected; measure *actual* Agent deviation, refusal and token overhead, not just candidate counts.
- If PACT does not outperform the direct-ADR control on decision adherence **without excessive owner prompts or real overhead**, leave default behavior unchanged; simplify or remove mechanisms rather than expand long-term notes.
- Release remains **HOLD** until independent comparison, owner observation and the original acceptance ledger justify GO. No new mandatory project documents, automatic note writes, vector index, graph scanning, Version bump, release tag or changes to non-PACT repositories are authorized by this handoff.

## 5. Minimum runnable approach when provisioned

An authorized custodian may execute the CLI via **official** `codex exec --sandbox workspace-write --json` in a separate ephemeral clone and stream its JSONL to the custodian-only receipt store; the official [Codex non-interactive reference](https://learn.chatgpt.com/docs/cli/reference) documents the CLI. The official [Codex GitHub Action](https://github.com/openai/codex-action) requires an explicitly provisioned provider API key and must be configured with least privilege. **No key, runner, real run or secret is configured by this document.** Another real host (Claude Code or OpenCode) is eligible only with its own verifiable version/permissions and identical study constraints.

Current executable work completed: merge #219/#220 and verify source-only real-repository installed Context. **Not completed**: independent custodian's holdout, authorized Agent runs and observed Owner-value study. Their blocker is an external trial precondition, not something CI or the synthetic benchmark may attest to.
