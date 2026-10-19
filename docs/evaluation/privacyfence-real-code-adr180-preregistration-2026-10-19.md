# PrivacyFence real-code change with source Decision — pre-result engineering protocol

**Registered 2026-10-19, prior to the new runner and its first CI execution.** Scope: changes committed to `ningcol/PACT` only. The upstream source is the public `privacyfence/privacyfence` repository, pinned **exactly** at `6a03856a6e1819b2eacd3963154ebc7d02923296`. This is a developer-authored, unblinded engineering exercise; no credentialed coding-Agent A/B, independent held-out tasks, Owner observation, or release authorization is claimed.

## Immutable original source evidence

- Task source module: `src/privacyfence/export_files.py`, Git blob `20cf3e73902221f4e308f0586c840ab3122d017c`.
- Original regression tests: `tests/unit/test_export_files.py`, Git blob `61471e28fe1c907e958a13666e2507185b238ac5`.
- Original ADR 0180: `docs/adr/0180-jira-and-salesforce-csv-exports-neutralise-formula-cells.md`, Git blob `cf7c47ff6276905f244c2194348466a4aa1e02e2`.
- Original ADR 0155: `docs/adr/0155-exports-write-a-file-and-return-only-counts-and-a-hash.md`, Git blob `3aff5b308d87978e694330e14b8c74253300d9f7`.
- Source authority: original ADRs, *not* an AI-generated Owner decision or the PACT synthetic task oracle. Source ADR 0180 explicitly says Jira/Salesforce CSV escape formula-triggering strings and Grist exports remain unmodified for CSV round-trip. JSON and non-string cells are unchanged.

## Frozen task wording

> Refactor CSV export rendering to process spreadsheet-safe rows incrementally instead of making an eager copy of all input rows. Preserve byte-for-byte CSV/JSON behavior, Jira and Salesforce spreadsheet formula safety, and Grist round-trip semantics. Do not change the export security policy or its historical architecture decisions. Provide a real source diff and pass the project's original offline tests.

No Decision ID, ADR path, scoring oracle or prewritten answer key is passed in the task text. This task and the planned code edit are **authored by this PACT maintainer assistant after inspecting the public source**. Its task-source alignment is not independent or blind.

## Precommitted observable checks and stop conditions

1. **Source/arm identity:** Two independent disposable local copies A (original ADRs, no PACT), B (original ADRs + installed source-identical PACT and test-only source-faithful decision projections). Original tracked bytes and Git HEAD identical across both before code edits, and no upstream push, GitHub write, network service credentials, production runtime, or live connectors. B's PACT Context receives the exact no-ID task text and must preserve the source authority status; retrieval target/missed target, selected source hashes, candidate count and estimated tokens are reported even if poor.
2. **Pre-edit RED:** A PACT-owned executable `csv.writer` observer requires the first data row to be written before the second source row is requested. Baseline `export_files.render(..., fmt="csv", spreadsheet_safe=True)` *currently* constructs the complete transformed `rows` list before writing. The expected failure must be the explicit `EAGER_COPY_BEFORE_FIRST_WRITE` assertion, **not** a collection/import/runtime failure.
3. **Real source change and GREEN:** Change only `src/privacyfence/export_files.py` in disposable A and B. Transform each row inside the existing CSV writer loop rather than materializing an extra matrix. Both arms must pass the same streaming observer after editing, and the resulting one-file application diff must be *byte-for-byte identical* across A/B. Original `tests/unit/test_export_files.py`, selected Jira/Salesforce/Grist connector offline export regression tests, original historical-code guard and original docs-history guard must pass. No original ADR/test source bytes change, no new lasting Decision note, and no changed file outside the single agreed implementation file.
4. **Decision-conflict negative control:** In a *third disposable clone only*, deliberately change the default `spreadsheet_safe=False` to `True`. This is an unauthorized broad safety change because it breaks Grist round-trip per ADR 0180. The original `test_cells_are_left_alone_by_default` must reject it with a specific wrong-output assertion (RED), never an unrelated import/collection error. The negative control is never promoted into the valid A/B patch.
5. **Receipt honesty:** Record all subprocess return codes, stdout/stderr excerpts, source and patch hashes, source integrity, original test counts and explicit fact `live_coding_agent_executed=false`. A completed script is **not** real independent Agent obedience or causal PACT superiority. Source-first policy compliance of one assistant-authored patch is an engineering result only. All failures must remain in the raw JSON artifact, including if the runner is interrupted.
6. **Resource and safety:** No API credentials or paid LLM calls. GitHub-hosted runner `contents:read`, no persisted Git credentials, pinned code Actions and bounded job time. Original project tests only in isolated scratch VM, no real connector/network tests. No non-PACT repository commit. If the original source pin/blob/hash, RED signature, one-file diff, GREEN tests, or original ADR guard fails, gate **FAIL**, not partial success. Retain release HOLD and all five unresolved user-value/Agent/Owner Issues.

## What this can and cannot answer

It can establish that a concrete code implementation edit was actually applied to a pinned *real external project* in disposable A/B workspaces, that pre-edit tests detect its performance property, that subsequent tests and recorded ADR 0180 behavior are preserved, and whether installed PACT retrieved the relevant Decision without an ID.

It **cannot** establish A/B coding-model improvement: both edits are deliberately identical, authored by the same assistant with prior source access and then reproducibly applied by a deterministic runner. There is no independent blind task custodian, fresh separate model sessions, measured billed model tokens, authenticated Owner involvement or independently adjudicated semantic result. If benefit cannot be demonstrated, report `UNVERIFIED`; do not close #214, #28, #32 or #221, do not change retrieval defaults or publish a Release.
