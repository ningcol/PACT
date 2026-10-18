# PACT #221: Brownfield decision noise probe — author-labelled preregistration

Freeze date: **2026-10-18**, PACT main baseline `8d10a7bfde791a84da12742e2302704f706fd796`.
Public upstream [mrwilson/adr-viewer](https://github.com/mrwilson/adr-viewer)
pinned `a25f1c71e031bdaa63fe3175f969f197139f2044`, original six
unchanged ADR source files and the **same test-only** minimally projected
Decision set used in merged PR #220. No upstream repository writes.

This is **exploratory engineering**, not an independent blind study: task author,
labels and evaluator are all PACT development-controlled. Public authored task
answers must not be supplied to any later formal Agent holdout. No actual coding
Agent, Owner, real model tokens, semantic obedience or GO decision is measured.

## Frozen before implementation

- New authored tasks: 12 total, eight routine negative controls and four
  decision-conflict positive controls. Text, IDs, classification and predicted
  current Decision IDs are in separate `noise-cases-v1.json` and
  `noise-developer-oracle-v1.json`; freeze Git blobs before writing runner
  or changing Discover behavior.
- No ID or expected match is passed to the installed PACT `discover` or
  `context` commands. Both A=unadapted original ADRs and
  B=projected PACT Decision metadata have identical task, intent work,
  four knowledge file limit, 2048 estimated-token budget, low risk,
  no-code selection, target and source SHA.
- Preserve scores, lexical reasons and selected source hashes where available.
  Every negative case returning a current Decision counts as **noise**
  under the developer task labels, not as a confirmed semantic false positive.
  Track actual target recall per positive case, extras, affected negative
  cases, note count, estimated context tokens and source immutability.
- Start with unchanged PACT baseline to reproduce the RED. Do not optimize
  case wording or oracle after seeing results. Fix only a proven
  lexical/scope cause, record old and new runner SHAs, and repeat with
  exact same frozen tasks. Changes cannot be interpreted as causal Agent
  benefit.
- Require no regressions for exact-ID/title/alias queries, historical
  supersession, required confirmed Rules, and unrelated code-symbol search.
  Generic-language and multilingual tokens require separate checks; an
  English-only noise improvement is not proof all languages are solved.

## Classification and stop

- **Engineering FAIL** on source tampering, unexpected durable note change,
  incorrect authority upgrade, malformed installed CLI, schema violations,
  source-archive mismatch, wrong frozen source/blob/denominator or lost raw
  failure receipt. Preserve full JSON.
- **Retrieval diagnostic HOLD** if any positive target is missing or any
  routine negative has an injected current Decision, irrespective of Python
  tests passing.
- If a lexical filter merely hides important current Decisions, revert and
  record the tradeoff instead of forcing PASS. Do not silently change
  defaults, default Agent instructions, mandatory memory, vector indices or
  external projects for this experiment.
- **Formal independent Agent/Owner acceptance** remains BLOCKED; #214 and
  release #63 stay OPEN/HOLD. These 12 public cases are excluded from
  the genuine blind protocol in #222.
