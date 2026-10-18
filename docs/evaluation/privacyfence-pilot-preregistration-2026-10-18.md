# PrivacyFence second brownfield pilot — frozen engineering design (2026-10-18)

**PACT-only changes; public upstream read-only.** This is a prospective *developer-designed retrieval diagnostic*, **not** a genuinely blinded coding-Agent A/B or an independently verified Owner benefit experiment. The original formal Agent study remains BLOCKED as described by `docs/evaluation/decision-memory-real-agent-blind-trial-2026-10-18.md` and issue #214.

## Immutable source and freeze-before-run order

- PACT base `09e78ed995fb7cedb5b21851833346274f5aec33`, directly after engineering PR #224 merged.
- Public Apache-2.0 upstream `privacyfence/privacyfence` pinned at `6a03856a6e1819b2eacd3963154ebc7d02923296`. No write credentials or upstream PRs. Its `docs/adr/` had 184 Markdown files at this commit.
- Source-doc paths, expected Git blobs, ten scenario strings and two unrelated routine negatives were first frozen in `benchmarks/privacyfence/pilot-cases-v1.json`; **Git blob `d0397c34bbed537b5a91a5d9340d52d21bc9460b`**.
- Developer-labelled expected target IDs and one never-authoritative **Proposed** ADR #0005 were then frozen in `benchmarks/privacyfence/pilot-developer-oracle-v1.json`; **Git blob `1f6cb98e38a529fb8012c49cbda7b19c9c4e59d0`**.
- These Git objects were committed before authoring the runner or running any case. Author labels are **not an independent sealed oracle**, and the ten positive tasks are **not certified independent Decision families** for the formal study.
- Preserve upstream source blob identities, untouched tracked files and `docs/adr` originals. Test-only PACT metadata projections must preserve the original words and recognized status, rebase relative links, and add **no aliases, confirmed Domain, code path or Owner sign-off**. Explicitly record known amended/partially superseded relationships as an interpretive limitation.

## Experiment and outputs

On an isolated disposable GitHub Actions runner, install the **actual compact PACT runtime from the exact checked-out source** and run the same 12 task-only queries, fixed limit 6, 4096 estimated tokens, low risk, `--intent work`, no code context:

- **A (unadapted):** all original ADR files are ordinary, unmanaged Markdown under `docs/adr`; no native PACT Decision metadata.
- **B (adapted):** identical original files plus test-only source-verified projections of the 12 pinned source ADRs. Ten are developer-labelled conflict targets, a supporting amended source is kept, and one source explicitly marked Proposed is projected as **proposed**, never `implemented`.
- Measure raw Discover/Context return codes, selected source paths, Decision recall, extra candidates, routine negative injection, estimated Context materialization cost, timing and source/status integrity. Never compare raw A's zero PACT Decision IDs to B as if it were a real Agent's recall.
- A run **fails closed for integrity** (pinned SHA/blobs changed, source modifications, fabricated status, missing/forged digest, failed subprocess/schema, unexpected knowledge growth or false promotion of Proposed). Recall and false positives are recorded even if bad and cannot be hidden with thresholds or case omission.
- A separate fresh job without the PACT checkout runs a narrowly selected set of existing **offline** PrivacyFence unit tests. Dependency provisioning in this disposable job is not access to live connectors. Report total/pass/fail/skip, never fabricate a baseline passing status.

## Test safety and interpretation

Use only a read-only public clone pinned by SHA and ephemeral local disk. The workflow has read-only repository token, `persist-credentials: false`, a bounded timeout and no secrets. No third-party code executes inside the PACT scorer job; upstream tests run only in an isolated separate job. Never call real Gmail, Slack, Salesforce or any provider API; no actual credentials are supplied. Published report excludes private content and secrets.

**Formal real-Agent comparative outcome stays BLOCKED**: no credentialed independent Agent runner, no independently withheld task/answer custodian, no true arm-blind semantic graders, no enforced model-usage spend ceiling and no authenticated Owner observation. If these prerequisites later become available, use a separate, prospective study: new questions and independently sealed answers, isolated real coding sessions, recorded diffs and model usage, and authenticated Owner involvement. Do not re-use these now-exposed cards for a confirmatory superiority claim.

**Release HOLD** and original #221/#214/#28/#32 stay open. No non-PACT repository writes, release/tag, new default-on retrieval policy, long-term memory mandate, background monitoring or fabricated completion receipts.
