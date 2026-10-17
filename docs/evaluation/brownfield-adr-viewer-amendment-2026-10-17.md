# Real external ADR pilot: pre-registered protocol amendment

Date: 2026-10-17. **Do not modify the original frozen task cards, oracle or source SHA pins.**

## Evidence from the first run (not erased)

PACT-only PR #220 first GitHub Actions run: https://github.com/ningcol/PACT/actions/runs/39010659394

- Public upstream `mrwilson/adr-viewer` was **actually cloned** at `a25f1c71e031bdaa63fe3175f969f197139f2044`, verified as unchanged after PACT adoption.
- Its original Python suite passed **19/19**, with one third-party deprecation warning.
- Compact PACT runtime installed and executed on the actual upstream clone; the six developer-authored (not independent) task probes produced 4/4 target hits **after** test-only metadata projection. Baseline raw ADR retrieval produced 0 target Decision IDs. There were **12 oracle-extraneous current Decision candidates**, including one injected on the ordinary `routine-typing` task. No actual LLM Agent obeyed or violated a decision.
- PACT `check` failed **four dangling internal links** in the **test-only projected copies**, because the original ADR Markdown files link to sibling documents under `doc/adr/`, while the projected files live under `.agents/decisions/{status}/`. This is a pilot adapter defect, **not evidence the original upstream ADRs are broken** and not a valid PACT release-readiness pass.

## Narrow correction, preserving the failed observation

Update only the projected copy's **relative Markdown sibling link targets** to `../../../doc/adr/<existing original filename>.md`; retain original Markdown labels, words, decision state, original upstream source files, all frozen tasks, IDs, expected targets, budgets and historical relationships. The base reference is still the same original `doc/adr` source. Do not rewrite status 0005 (amendment) as full supersession.

A focused regression verifies that upstream text is unchanged and each projected sibling link resolves to the original source path. Preserve first-run failure in CI history and in this amendment; do not silently consider it a successful test.

The unrelated candidate on a routine task and 12 oracle-extraneous candidates remain **retrieval-quality findings**, not grounds to change the frozen task wording or add an automatic graph scanner before independent evaluation. Keep retrieval effectiveness, real-Agent/Owner gates, and release **HOLD**.
