# M1 cold-start Decision-memory diagnostic — frozen case results

Date: 2026-10-17. Work confined to PACT and installed disposable temp fixtures.
**This is a synthetic engineering diagnostic, not a new-session real Agent,
independent blind oracle, authenticated Owner approval, or decision-obedience trial.**
Release stays **HOLD**. All M0 and M1 original task text/oracles remain unchanged.

## Pinned evidence and experiment integrity

- Baseline preregistration before evaluator: PR #219 commits \`3981860\`,
  \`fa9339a\`, \`7458955\`; frozen M1 task-card Git blob
  \`5b5c80d2f772c75d3c7984c0ffbc2d380870a6fa\`;
  developer-written oracle \`bba20149d96b624bc6d9cae09008b91a1c9bfe44\`.
- M0 frozen corpus (not M0 runner) blob:
  \`753babf70317c6af1b292b1b031e0afaec503ec3\`.
  Original M1 preregistration misidentified the runner blob; see
  [provenance amendment](decision-memory-m1-provenance-amendment-2026-10-17.md).
  The first CI failure was this instrument mispin, not a measured retrieval miss.
- Corrected M1 installed-runtime raw case-level JSON:
  [PACT Check run 39008679344](https://github.com/ningcol/PACT/actions/runs/39008679344),
  PR #219 source head \`81ffd5afc48fc67ed8b062f53403cda151c67e8a\`.
  All eight case outputs (including extra Decisions and counts) were printed.
  The GitHub Actions \`pact-check\` job succeeded.
- On original pre-stopword code, the M1 installed regression failed with
  \`routine-docs: unrelated routine task received current Decisions\`:
  [Core Matrix 39008241172](https://github.com/ningcol/PACT/actions/runs/39008241172).
  A focused additional RED was registered before the smallest word-filter
  change in \`discover.score_document\`. Original input cards were never tuned.
- On Windows an independent checkout newline issue caused false frozen
  file-tamper detection, fixed by text CRLF→LF Git-blob normalization. No
  semantic input/answer content was relaxed.

## Raw diagnostic summary after the scoped lexical noise repair

The installed compact \`pact.pyz\` was used. Arm A uses only the task text,
low risk, work intent, \`--no-code\`, 4 knowledge artifacts, 2048 estimated
tokens. Metadata-only B uses the public changed paths to enumerate exact
Project Map \`paths\` matches; B **never enters Context** and is not an Agent
retrieval arm. All eight frozen developer-authored cases stay in denominator.

| Case | A target Current Decision | A extra current candidates outside oracle | B exact-path candidate for target | Specific caveat |
| --- | --- | ---: | --- | --- |
| Cache ownership conflict | found | 0 | found | Rejected rationale is evidence, not authority |
| Broker local counter | found | 2 | found | Several irrelevant current candidates also selected |
| Pathless counter | **MISSED** | 2 | **MISSED** | No path or shared vocabulary; cannot infer absent decision |
| Renamed ingress | found | 3 | MISSED | Stale \`src/account/legacy_bridge.py\` anchor remained |
| Partial webhook supersession | found | 3 | found | Source can be retrieved but surviving clauses need semantic review |
| Rejected global cache | found | 1 | found | Rejected historical explanation retained |
| Wire format contract | found | 3 | found | Other current decisions still contaminate candidate Context |
| Routine documentation | n/a; no current Decision | 0 | n/a | Prior unrelated-memory injection regression now passes |

**Oracle-weighted target recall:** 6/7 = **85.7%**. **One** target
Decision missing. Across seven target-positive cases, A selected **20**
current Decision candidates: six oracle targets and **14 outside** the
developer oracle (oracle-proxy candidate precision **6/20 = 30%**). These
14 are *oracle-extraneous candidate IDs*, not independent judgments that
14 actual business constraints are wrong. They nevertheless show substantial
context noise, so high recall by itself is not success.

A plus the B diagnostic has the **same** developer-oracle target coverage
(6/7); exact-path metadata does not recover the pathless miss and loses
the renamed path where A happened to recover by lexical wording. This does
**not** justify rolling out a global path scanner or calling B a better
retriever. The historical candidate links in B are still review-only.

Knowledge source files remained **9 before / 9 after** with unchanged
hashes. This shows the *read-only tool trial* did not add durable notes; it
does not measure whether a real Agent over-writes decisions or creates too
many memories. Candidate Context \`status=candidate\` likewise proves
neither reading nor obedience. Model tokens, Owner escalations and human
time remain \`null\` / unverified.

## Product GO/NO-GO

- **Synthetic instrumentation and status safety: PASS** at the cited run,
  including no historical \`rejected/superseded\` authority promotion and
  no unrelated routine Decision insertion after the targeted repair.
- **Unknown-decision cold-start reliability: NO-GO/HOLD.** A target
  Decision was missing, and 14 other implemented Decision candidates were
  present beyond the test oracle. The score cannot be inflated by B hints.
- **Independent real Agent obedience and Owner value: UNVERIFIED/BLOCKED.**
  No independent holdout custodian, authorized real Agent, source-change
  semantic reviewer or observed Owner controls participated. Do not close
  #214/#28/#32 or release-gate #63. NO TAG/RELEASE.

## Review notes (scoped self-review; not independent approval)

1. **Measurement contract:** corrected a misidentified initial source blob
   without changing pre-frozen tasks/answers; verified CLI has no hidden
   Decision-ID hint; preserve all runs and nonzero JSON on failures.
2. **Authority/memory boundaries:** targeted the reproduced unrelated
   lexical injection; kept code-path/symbol ranking unchanged; retained
   historical Decision status; verified extra synthetic candidates are
   reported instead of silently turning into applicable Product Rules.
   Added non-Markdown note detection and materialized-ID consistency
   regression after the initial metric run.
3. **Portability and evidence:** fixed checkout CRLF-only SHA mismatch,
   registered M1 tests on the 3 OS × 3 Python matrix, and moved M1 raw
   JSON publication ahead of the full unittest step so a FAIL is not
   masked. Exact-HEAD CI evidence is required after the last changes.
   These are self-review passes, **not** an independent blind code review.

## Next bounded step

Before increasing default retrieval scope, preregister a genuinely unseen
cold-start Agent test where the evaluation custodian, not the implementer,
holds expected Decisions and supplies only task wording and code. Measure
source-level decision obey/override decisions, irrelevant memory injection,
rationale precision, clarification overhead and actual model context size.
When Agent runners or Owner observations are unauthorized/unavailable,
record \`blocked\`, keep Release HOLD, and restrict changes to PACT-only
engineering. Separately investigate the pathless miss and candidate noise
under fixed budget/precision gates; avoid growing the long-term store.
