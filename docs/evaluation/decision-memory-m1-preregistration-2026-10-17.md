# M1 preregistration — cold-start Decision guard, PACT-only

Date: 2026-10-17. Base main `b96a64485e1c855c5caeedb2a2addcd766f6398b`.
Source corpus: immutable M0 fictional case documents in `benchmarks/decision-memory/m0-inputs.json` (blob SHA `14693c6b209b8ef734edbd9e3e9842efd5bca3cd`); M0 must **not** be modified to make M1 succeed. Freeze this document, `m1-task-cards.json`, and `m1-oracle.json` in Git history **before** writing/running M1 evaluator. Any post-freeze changes require a separately documented version and cannot replace a failed score.

## Questions and strict evidence classification

1. Does a cold-start task with **no historical chat, supplied Decision ID, target oracle or related hint** retrieve the applicable implemented Decision using the **installed** PACT Context CLI?
2. How much can **bounded, code-path-only metadata navigation** indicate missing Decision candidates, given only the paths named on the task card? This diagnostic is NOT a Context retrieval success and NOT an Agent reading or obeying a Decision.
3. Does routine work avoid creating long-lived Decision files? Do rejected/superseded Decisions remain history rather than automatically becoming current authority?
4. Can a *separately authorized real Agent* locate and **respect** the rationale, recognize conflicts/partial supersession, and escalate actual changes in Owner meaning instead of silently overwriting it? **This cannot be answered by the synthetic harness.**

The frozen eight case cards and developer-authored oracle are **not independent**; the corpus itself is reused from M0. A simulated A/B may reveal mechanics but is not a real, blind, held-out or independent Agent/Owner evaluation.

## Frozen arms (no privileged hints)

- A: Installed `pact.py discover TASK --intent work --json` and `pact.py context TASK --success ... --risk low --intent work --no-code --limit 4 --token-budget 2048`. No `--query DEC-*`, no `--require-rule`, no oracle-derived expansion. Store every hit/miss and subprocess failure.
- B **metadata-only diagnostic**: Start with the **identical** A result; inspect the installed generated Project Map and match `paths` **exactly** to the task card's public `changed_paths` (max 4 path candidates); report matching current and historical Decision IDs separately. Do **not** place B hints into Context, auto-promote status, alter rank/defaults, or report B as actual Agent recall. Missing and stale path anchors remain misses.
- Both: fixed M0 fictional installed-runtime corpus, same low risk/count/token budget, deterministic document hashes before and after. Generated disposable indexes are allowed; added/changed project Decision/Rule source files are not. No other repo may be written.
- Oracle file lives **outside** installed fixture. Only open it after *all* A/B predictions are collected and temp installation removed; never accept arbitrary fixture paths or echo oracle to subprocess argv.

## Predeclared gates and interpretation

Hard instrument/safety FAIL if any CLI/subprocess error, malformed/unknown score entry, oracle leak into installation, incorrect status promotion (`rejected`/`superseded` into current Decisions, nonconfirmed Rules into required Rules), changed/new Decision/Rule files, extra mandatory PACT memory, or out-of-budget materialized Context. Emit **complete JSON before nonzero exit**, including failures. All eight cards remain in denominator; absence of targets on the routine card must not mask misses elsewhere.

Efficiency: record per-case installed Context elapsed time, selected estimated tokens, knowledge count, additional navigation hint count; do not call crude estimates *real model tokens* or claim a generalized SLA.

Decision-memory effectiveness: no automatic PACT default rollout unless **every target-bearing high-impact case** has its required Decision available to an independent cold-start real Agent **and** a separate semantic reviewer sees no silent decision replacement, no historical authority promotion and no false-done. The diagnostic can instead report `HOLD` on misses. A known-ID upper bound from M0 is not an eligible M1 treatment.

Human value gate: real Agent task/Owner oversight, true held-out tasks, independent evaluation/stop rules, measured cost/time and Owner feedback require explicit authorization and provenance. When missing, record `null` / `unverified`, never infer zeros or claim release readiness. Original #214 and pilot #28/#32 stay OPEN, Release HOLD under #63.

## Real Agent trial packet (not executed by benchmark)

A separate custodian must create a clean installed temporary checkout **without the PACT source checkout, M0/M1 oracle, scoring scripts, reports, or old chat**. Provide the Agent only the synthetic project's task card, code and its project PACT installation. Request it to: (a) find relevant earlier decisions without an ID hint; (b) quote their exact IDs and rationale with evidence; (c) identify proposed conflicts, surviving constraints and changed assumptions; (d) either maintain them or explicitly request Owner meaning approval **before** implementation; (e) avoid authoring a new Decision for routine work. Capture the real Agent/model/version, fresh session, initial/last SHA, exact commands, timestamps, produced worktree diff, Evidence/Owner observations and **every** failed attempt. Custodian retains unseen oracle, scores every attempt, and independently checks the output against sources. If any contamination, unauthenticated approval, or omitted negative case occurs: STOP, preserve raw evidence, NO-GO.

No real Agent or Owner is run merely by adding this packet to GitHub. No tagging/release or downstream repository changes.
