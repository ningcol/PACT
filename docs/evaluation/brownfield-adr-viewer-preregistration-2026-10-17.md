# PACT brownfield pilot: pinned public adr-viewer (pre-run registration)

**Freeze date:** 2026-10-17. **PACT parent SHA:** `4c7416f2c24375fa61929e80b135a66036cf1320`.
**Repository selected:** [mrwilson/adr-viewer](https://github.com/mrwilson/adr-viewer) (MIT, real Python program and existing project-authored ADRs).
**External immutable commit:** `a25f1c71e031bdaa63fe3175f969f197139f2044` (not moving `master`).
This pilot is a **real source-repository onboarding/retrieval exercise**, but **NOT** an independent cold-start LLM Agent trial or observed Owner behavior.

## Source isolation and immutable data

- Keep the original public GitHub repository **read-only**. Work in a fresh temporary copy cloned by GitHub Actions; never fork, push, create issues/PRs, or edit the external remote.
- Pin exact GitHub SHA and each of the six original ADR Git blob hashes in `benchmarks/brownfield-adr-viewer/pilot-cards.json`. Verify before writing anything.
- Do not claim the external project's ADR authors approved PACT. Preserve raw original ADR files unmodified. An adapted PACT Decision with `implemented` status is **only a test interpretation of upstream ADR's Accepted state**, not authenticated Owner approval.
- Adapt only source-authored title, status, unaltered ADR prose and explicit supersession 0003→0004. Do not invent aliases/paths/keywords; do not transcribe hypotheses as owner rules. `0005 Amends 0004` is **not** whole-document supersession.
- Copy a minimal PACT runtime using `scripts/pact/init.py --target TEMP --apply`, test installed `pact.py`. No persistent notes in the PACT repo. Any generated Decision belongs only to disposable upstream fixture.
- Stop and mark invalid if the cloned source SHA/blobs differ, tests alter original tracked source files, unauthorized writes occur, any nonconfirmed Decision is promoted to current authority, or original ADR bytes changed.

## Frozen questions and protocol

Use six developer-authored task cards; four conflict tasks and two ordinary tasks. No Decision IDs, oracle targets, or extra query expansion in the Agent-facing task text. The oracle is prepared in a **separate committed file before the runner**; it remains authored by the implementer, not an independently withheld oracle.

Phase A — plain installed PACT after clean init, with the real original `doc/adr/*.md` left untouched. Measure direct `context --intent work --no-code` and do not assume PACT recognizes legacy Markdown without metadata.

Phase B — on the same pinned temporary source (untouched upstream tracked files), add only six projected `.agents/decisions` records, derived from original upstream ADRs. Run identical task wording, budget and PACT CLI, no hint ID or external semantic ranker. Record every prediction **before** opening the PACT-owned scoring oracle. Track selected current Decisions, historical candidates, unrelated decisions, context count and estimated tokens. Baseline A vs metadata-adapted B is an **adoption cost diagnostic**, *not* a causal real Agent PACT-vs-control benefit test.

Both phases: explicitly record initial/install/adapted source hash status; run original upstream `pytest` if dependencies install, but do not count third-party Python tests as PACT Agent obedience. Preserve failures and stop masks. Include a routine task to test irrelevant Decision injection and note cardinality.

## Before-observation acceptance rules

- **Engineering safety PASS:** correct immutable source/checkouts, `pact check` passes, installed CLI exits zero, no false authority promotion, no source ADR mutation or extra long-term note beyond six projected Decision files, no 4-item count overrun. On any safety FAIL, save complete JSON and exit nonzero.
- **Decision retrieval GO:** all four current target Decisions selected and **zero extra current Decisions on either routine case**, within fixed budget; if a target is missed or routine case gets a Decision, retrieval is `HOLD` regardless of safety status. Extraneous candidates in positive tasks are counted, not assumed acceptable.
- **Semantic obedience GO:** unavailable until an independently authorized real Agent makes or declines changes in a fresh session and a separate reviewer grades alignment. A CLI path in the candidate envelope is not proof it was read or respected.
- **User value/release:** authorized Owner comprehension/time/clarification and an independent blind Agent comparison are absent, keep `null` and `HOLD`; never release or mark #214 complete on this pilot.

The script and workflow must be committed **after** these frozen inputs and protocol. Any later metadata, evaluator or regression correction must be disclosed in a separate amendment; no changing task text or oracle to pass.
