# PACT real GitHub brownfield pilot: adr-viewer result (2026-10-17)

## Nature and source of evidence

This is a **genuine remote GitHub repository cloned into a disposable GitHub Actions runner**:
[mrwilson/adr-viewer](https://github.com/mrwilson/adr-viewer), fixed commit
`a25f1c71e031bdaa63fe3175f969f197139f2044`, six project-authored legacy ADRs.
It is a real source/onboarding + installed-runtime retrieval test, but six task cards and
the oracle were **written by the PACT implementer**, not independently held out.
**No real LLM Agent executed code changes, no Owner approved PACT and no semantic obedience
was observed.** Original source ADRs were left unchanged; no changes pushed upstream.

PACT source parent: `4c7416f2c24375fa61929e80b135a66036cf1320`
(M1 branch/PR #219). Pilot is an isolated stacked PACT PR #220, not on `main`.

Pre-run tasks/oracle/source pin:
[preregistration](brownfield-adr-viewer-preregistration-2026-10-17.md);
[frozen task cards](../../benchmarks/brownfield-adr-viewer/pilot-cards.json);
[frozen developer oracle](../../benchmarks/brownfield-adr-viewer/pilot-oracle.json).

## Runs, preserved RED, scoped adapter correction

- First RED: [Actions run 39010659394](https://github.com/ningcol/PACT/actions/runs/39010659394).
  The external clone succeeded, **19/19 original Python unit tests passed**
  (one `bottle` deprecation warning), PACT installed and produced case-level
  retrieval observations. However, PACT `check` flagged **four broken internal Markdown
  references** in *test-only copies* of original ADRs, because their sibling links had not
  been relocated from the original `doc/adr/` directory. This was an adapter bug,
  not a mutation of the upstream ADRs or a verified core-runtime defect.
- Scoped fix: only rebase relative links in projected copies to
  `../../../doc/adr/<original-name>.md`. The original ADR files and all frozen
  task inputs/oracle/source SHAs remain unchanged. See
  [preserved amendment](brownfield-adr-viewer-amendment-2026-10-17.md).
- First successful end-to-end engineering run after this correction:
  [Actions run 39010792207](https://github.com/ningcol/PACT/actions/runs/39010792207),
  PACT commit `92f846339585586fc3b094555c96dd0bc2e57c5d`.
  `pact check` returns zero, original upstream code stays tracked-clean,
  exactly six **test-only** Decision files are created and remain unchanged by
  retrieval, and the raw case-level JSON is retained as a GitHub artifact.
  The current later PR SHA also requires exact-head CI before merge.
- Cross-platform source-tests and main PACT Check are independent CI gates;
  upstream unit tests are not evidence of PACT Agent decision adherence.

## Frozen no-ID retrieval results

All six cases use the installed compact `pact.pyz`, `--intent work`, `--risk low`,
`--no-code`, four knowledge artifacts and estimated 2048-token budget.
A = original source files left as legacy Markdown, after PACT init but before translation.
B = only source-derived PACT Decision metadata/prose and existing 0003→0004
full supersession relation added to the *disposable clone*; no aliases or task-linked
`paths` invented. Original 0005 amendment is not treated as supersession.
This is **not** a genuine Agent A/B causal comparison.

| Frozen task | A legacy current ID retrieved | B correct current Decision | B other current Decisions | B historical 0003 in discovery |
| --- | --- | --- | ---: | --- |
| Remove command-line entry point | no | 0002 found | 3 | n/a |
| Treat superseded/accepted headers equally | no | 0004 found | 3 | **no** |
| Remove visual amendment distinction | no | 0005 found | 2 | **no** |
| Replace accessibility cues with color alone | no | 0006 found | 3 | n/a |
| Routine README spelling | no | none (correct) | 0 | n/a |
| Routine import ordering | no | none (correct target) | **4 unwanted** | n/a |

**A raw legacy PACT Decision target recall: 0/4.**
**B minimally adapted Decision target recall: 4/4.**
But B selected **19** current Decision candidates total across six cases:
only 4 were oracle targets; **15 were extra**, so oracle-proxy candidate precision
was **4/19 = 21.1%** (NOT validated semantic precision). On one of two routine
tasks, B injected four Decisions despite no relevant durable choice.
The read-only retrieval evaluation did not create any further notes beyond
the six manually projected test fixtures.

One important honest caveat: the first pre-link-fix run selected **12** extra
current candidates; the safe link-target rebasing changed discoverable text and
the subsequent accepted run selected **15**. Both sets of observations remain.
Do not represent link rebasing as a retrieval-quality improvement or cherry-pick
the earlier lower noise number.

Selected-file estimated tokens in A stayed ~448 in this environment, vs B
~448–1271; they are file-size estimates, **not** actual LLM prompt tokens.
No independent model tokens, Owner clarification count or Owner time exists:
record those as `null`, never zero.

## Interpretation and stop gates

**Engineering integration: PASS** at run 39010792207. Original repository tests
pass, exact pinned source and original ADR blobs are intact, installed PACT checks
pass, no historical `superseded` artifact becomes a current Decision, and task
oracles are not passed through CLI.

**Core decision-memory goal: HOLD/NO-GO.** Correct decision IDs were found after
manual adaptation, but there was substantial collateral Decision injection,
historical rationale was not surfaced for supersession/amendment review under the
frozen top-four discovery budget, and real Agent compliance was not measured.
A new Agent cannot be said to 'remember and respect' an old Owner choice based
on this candidate envelope.

Do not infer the owner of upstream ADRs approved a PACT status change. The
projection maps `Accepted`→`implemented` for a disposable engineering
experiment only. Real Owner authority is outside this experiment.

Next evidence-based work: reproduce and isolate routine-task false injection
in the existing PACT retrieval code without overfitting these task cards,
then assess counterfactual negatives and an independently held-out real Agent
run under the *same* immutable repo baseline. Do not add a vector database,
automatic knowledge writes, blanket constraints or default scanner from these
six author-curated cases. Original #214/#28/#32/#63 release and real-benefit gates
remain **OPEN/HOLD**. No tag/release, no external GitHub write.
