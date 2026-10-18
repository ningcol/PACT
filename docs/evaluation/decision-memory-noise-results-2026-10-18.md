# Decision-memory noise: real pinned source, new developer-labelled cases (2026-10-18)

**Scope**: PACT only. Public project [mrwilson/adr-viewer](https://github.com/mrwilson/adr-viewer)
at `a25f1c71e031bdaa63fe3175f969f197139f2044`. Trial on installed
PACT compact runtime, with six source-ADR projections in a throwaway clone.
Original repository is read-only and tracked source was unchanged.

This is a **developer-authored/nonblind retrieval diagnostic**, NOT independent
task design, real LLM Agent execution, authenticated Owner approval or a
release-readiness study. Frozen task cards/oracle were committed before
the diagnostic runner. No new durable Decisions were created *except six
explicitly projected testing copies* inside the ephemeral fixture.

## Source and method

- [Immutable tasks](../../benchmarks/decision-memory/noise-cases-v1.json), Git blob
  `9d30fd10a7f2befca9b111542115a3d506bf82e5`.
- [Developer labels](../../benchmarks/decision-memory/noise-developer-oracle-v1.json),
  Git blob `fb8fc5960b98e3e68195b78f14cbd45431fae367`.
- Baseline PACT `8d10a7bfde791a84da12742e2302704f706fd796`,
  `work` intent, four knowledge sources, estimated 2048 tokens, no-code,
  low risk. A original legacy ADRs without projected PACT Decisions;
  B original ADRs plus test-only metadata projections. The two conditions
  are *adoption/format diagnostics*, NOT Agent A/B causal performance.
- The installed score/reasons, concrete Context selected Decisions,
  original content hashes, input order and failed subprocess output are
  retained in full JSON Actions artifacts. The developer oracle was opened
  only **after** all A/B predictions.
- [Run 39099137245](https://github.com/ningcol/PACT/actions/runs/39099137245):
  original pilot instrument got **engineering PASS** on the pre-fix lexical
  baseline. Later exact-head reruns add new fail-closed safety checks and
  lexical-source field attribution without modifying PACT runtime ranking.

## Pre-change retrieval results, 12 new tasks

| Metric | Observed | Interpretation |
| --- | ---: | --- |
| New cases | 12 | 8 routine, 4 conflict |
| Conflict target Decision IDs found | **4/4** | Developer-oracle retrieval proxy, not semantic obedience |
| Routine cases receiving uncalled-for current Decisions | **8/8** | Developer-labelled noisy Context selection |
| Extra current Decision candidate slots, all tasks | **41** | 30 on routine tasks + 11 on conflict tasks |
| All current Decision candidate slots | **45** | Four developer target slots plus 41 others |
| Total estimated Context tokens A, over 12 | **4,928** | CLI estimator; no model used |
| Total estimated Context tokens B, over 12 | **12,623** | +7,695 estimated tokens; NOT model tokens |
| Original source changed | **no** | Direct Git tracked state/ADR blob verification |
| Engineering safety | **PASS** | Installed PACT project check and source identity verified |
| Real Agent, Owner or independent blind set | **none** | Original acceptance **HOLD** |

The instrument's developer-labelled no-target labels should not be
mistaken for an independent semantic irrelevance adjudication.
The older six-case PR #220 noise count of 15 is on **different task wording**,
so 41 versus 15 does not constitute a time-series regression.

## Mechanism confirmed by per-hit source/lexical traces

1. `scripts/pact/discover.py` tokenizes English input with `[\\w\\-]+`
   and scores generic prose with `term in title/body`, **substring**
   rather than full-token membership. Neither the recent stopword set nor
   title/alias checks removes extension fragments or possessives.
2. `parse.py` and `server.py` contribute the token `py`: among eight
   routine tasks, **6/8** had a selected Decision lexical match involving a
   short (under three-character) term; **24** such term match appearances
   occur across its scored Decision hits. The source trace confirms these
   `py` matches frequently occur only as a substring of e.g. `Python`.
3. The possessive `README's` leaves an independent `s` token, matching
   unrelated Decision titles. The substring `unit` can match words such
   as `opportunity`; the trace records `substring_only` matches for
   **7/8** routine tasks (28 match appearances).
4. The *test-only* projection adapter repeats
   `Source (unchanged, project-authored)` in every projected note.
   Consequently the ordinary task's word `unchanged` appears in four
   Decisions without supporting task applicability. This diagnostic
   artifact is present in **3/8** routine cases (12 term appearances).
   **Do not claim production Owner-authored PACT Decisions necessarily
   exhibit the same rate**. Common metadata/disclaimer prose can pollute
   any generic lexical scorer, but this specific phrase is test-only.
5. Finally the explicit `work` intent ranks a current implemented Decision
   ahead of ordinary documents for any positive lexical score, even a
   sole incidental substring. This **magnifies** the low-confidence lexical
   hits into Context/Decision slots. Exact-score reasons are often empty,
   since the generic term loop adds points without a named reason.

The evidence establishes a mechanical path for noise, **not** that a real
Agent actually followed an irrelevant rule or falsely changed an Owner
decision. It also establishes an important risk of naive cleanup: in the
same new set the accessibility Decision is located from ordinary language
such as `screen reader`, even when the title/ID are absent. A blanket
score threshold or weak-match drop could hide important *pathless*
decisions, contrary to PACT's primary goal.

## Decision and next gate

- Keep existing default/opt-in runtime ranking unchanged in this
  diagnostic PR. It is **not** safe to mark #221 fixed based solely on
  these author-labelled negative controls, or remove weak Decision
  candidates merely to improve apparent precision.
- Candidate fixes worth measuring separately before default adoption:
  lexical boundary/tokenization normalization (including file extensions
  and possessives), de-noising **only** repeated boilerplate in projected
  notes, and explicit confidence/scope annotation that preserves
  applicable current Decisions. Measure each against unseen positive,
  negative and pathless/renamed-source cases before changing defaults.
- No mandatory new Notes, blanket decision scans or vector index.
- Issue #221 stays **OPEN**. The original real Agent/Owner acceptance
  issue #214, blind study prerequisites from #222 and release #63 stay
  **HOLD**. Project Version and external repositories remain untouched.
