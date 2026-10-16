# S3 fixed-input installed intent experiment — engineering only (2026-10-15)

> **Historical evidence snapshot — 2026-10-15.** This file records the original stacked #185–#193 branches, NOT the current PACT `main` source or a completed 48-AC acceptance. The engineering slices were later selectively integrated via #201–#209; new release hardening is tracked by #210/#211. Original independent RED/holdout/real Agent and Owner evidence gaps remain open in #28/#32/#63. Do not treat the frozen SHAs, 2026-10-15 version claims or run IDs below as current merge-SHA certification.


> **Scope:** PACT-owned fictional cache fixture, not a blind holdout, real Agent task, external production project, or verified Owner benefit. Never translate a CI result into a completed human/Agent S6/S7 V cell.

## Frozen measurement inputs and provenance

- Implementation SHA: [`c8516ae31659bdae28598ae971ebd272a3e229fa`](https://github.com/ningcol/PACT/commit/c8516ae31659bdae28598ae971ebd272a3e229fa), **before writing this report**.
- Real selected portability matrix: [PACT Core Matrix #38687324172](https://github.com/ningcol/PACT/actions/runs/38687324172), **9/9 success**, exact-job IDs listed below; installed CLI timing printed by `test_installed_intent_comparison.py` in `scripts/pact/tests/`.
- Full correctness smoke: [PACT Check #38687324164](https://github.com/ningcol/PACT/actions/runs/38687324164), **386 unit tests**, source + installed pyz + release asset/bootstrap smoke.
- Historical development replay: [PACT Brownfield Historical Benchmark #38687324175](https://github.com/ningcol/PACT/actions/runs/38687324175), **success**; **not an independently sealed holdout**.
- Disposable fixture: fresh PACT installation, 1 candidate-free confirmed Rule (`RULE-CACHE-001`), implemented Decision (`DEC-CACHE-CURRENT`), rejected alternative (`DEC-CACHE-REJECTED`) with conditions to reconsider, superseded historic Decision (`DEC-CACHE-OLD`) and ordinary README without PACT ID.
- Exactly the same primary query `cache`, explicit knowledge count `--limit 5`, `--token-budget 4096`, `--risk low`, `--no-code` in all four installed Context modes. Discover also has `--limit 5`; no supplementary queries in this particular comparison.
- `default` has **no** `--intent`; other arms specify `--intent work|decision|history`. Same fixture and CLI per OS/Python, sequential measurements, **one invocation per mode per job**.
- Each sample is subprocess wall-clock runtime observed on that GitHub runner; no controlled randomization, process-cost decomposition, warmed-state balancing or hardware normalization. These values cannot establish a statistically reliable speedup/cost saving.

## Runtime assertions and adoption rationale

| Mode | Actual installed fixture assertion | Decision |
| --- | --- | --- |
| Default | Exactly five lexical results, all five `(id,path)` pairs and order pinned, including ID-less README and old Decision; Context Envelope v1 and count/token policy unchanged | **Keep unchanged**; no new default-ranking behavior |
| `work` | First discovered item is the wholly confirmed current `RULE-CACHE-001` | **Optional only** for explicitly current-work retrieval |
| `decision` | First discovered item is an implemented or rejected Decision; rationale remains visible, without treating rejected choice as permanent business Rule | **Optional only** for targeted design reasoning |
| `history` | First discovered item is old/superseded or rejected historical Decision; no auto-promotion to business authority | **Optional only** for chronology/why investigation |

All four installed Context variants assert `status=candidate`, schema version 1, the same knowledge count/token limits, and inclusion of the confirmed Rule while never upgrading a rejected Decision to `applicable_rules`. Optional rank preference cannot override explicit stable-ID/title/alias matches; additional RRF multi-query and budget-one regressions separately exercise that behavior.

**Adopt/reject record:** adopt *exposure of three opt-in intent flags* as a controllable experiment because fixed-fixture behavior matches the intended retrieval modes without altering the default CLI or Context v1; **reject enabling the optional ranker by default**. We do **not** claim any new real-world recall advantage, reduced latency, lower tokens, improved Owner decisions or Agent usability. A future default/ranker adoption still requires separately preregistered, independently withheld holdout retrieval and matched task budgets. With no such evidence, keep no-intent behavior in force (the rollback choice), and S3 holdout/benefit acceptance remains `blocked/unverified`.

## Actual single-sample timings in milliseconds

| OS | Python | discover default | work | decision | history | context default | work | decision | history |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| macos-latest | 3.11 | 215.02 | 168.73 | 179.76 | 150.92 | 462.49 | 516.01 | 419.19 | 417.25 |
| macos-latest | 3.12 | 152.65 | 126.53 | 180.67 | 174.60 | 383.97 | 342.53 | 401.07 | 385.29 |
| macos-latest | 3.13 | 202.13 | 183.70 | 155.84 | 164.14 | 374.33 | 441.40 | 438.48 | 522.64 |
| ubuntu-latest | 3.11 | 134.98 | 131.03 | 130.02 | 130.27 | 320.71 | 322.72 | 323.74 | 329.45 |
| ubuntu-latest | 3.12 | 88.67 | 87.10 | 86.59 | 86.74 | 217.05 | 217.94 | 220.17 | 220.48 |
| ubuntu-latest | 3.13 | 90.89 | 89.02 | 90.91 | 113.29 | 221.58 | 222.09 | 227.50 | 233.67 |
| windows-latest | 3.11 | 339.37 | 325.86 | 291.91 | 304.22 | 712.12 | 708.11 | 707.74 | 712.83 |
| windows-latest | 3.12 | 329.65 | 237.48 | 243.13 | 239.14 | 578.78 | 584.32 | 584.07 | 582.86 |
| windows-latest | 3.13 | 189.81 | 160.72 | 159.98 | 155.82 | 383.77 | 385.90 | 380.79 | 375.92 |

## Descriptive medians only (across different runners, not causal estimates)

| Mode | Median installed discover (ms, n=9) | Median installed context (ms, n=9) |
| --- | ---: | ---: |
| default | 189.81 | 383.77 |
| work | 160.72 | 385.90 |
| decision | 159.98 | 401.07 |
| history | 155.82 | 385.29 |

The table is an *audit trace*, not a controlled benchmark. Python minor version and runner OS can move subprocess time materially, and these are one-shot warmed/cold mixed observations in a fixed invocation order.

## Scope of acceptance and remaining gaps

**AC-S3-01**: fixed input, exact count/token budget, installed default/work/decision/history test and adopt-opt-in/reject-new-default decision now have actual source/CI evidence. This is a **functional engineering experiment pass only**.

**AC-S3-06** remains **blocked**: no independent sealed holdout has measured non-degradation of relevant-file recall or real overhead. **AC-S3-07** remains **unverified** insofar as a *benefit-based* adopt/reject decision needs the holdout. S0's independently withheld oracle, S6 real Agent×layer 9-cell matrix and S7 real Owner effects are explicitly unsatisfied.

**Per-job log IDs**: `macos-latest/3.11` [116265047836](https://github.com/ningcol/PACT/actions/runs/38687324172/job/116265047836); `macos-latest/3.12` [116265047822](https://github.com/ningcol/PACT/actions/runs/38687324172/job/116265047822); `macos-latest/3.13` [116265047663](https://github.com/ningcol/PACT/actions/runs/38687324172/job/116265047663); `ubuntu-latest/3.11` [116265047815](https://github.com/ningcol/PACT/actions/runs/38687324172/job/116265047815); `ubuntu-latest/3.12` [116265047854](https://github.com/ningcol/PACT/actions/runs/38687324172/job/116265047854); `ubuntu-latest/3.13` [116265047706](https://github.com/ningcol/PACT/actions/runs/38687324172/job/116265047706); `windows-latest/3.11` [116265047946](https://github.com/ningcol/PACT/actions/runs/38687324172/job/116265047946); `windows-latest/3.12` [116265047840](https://github.com/ningcol/PACT/actions/runs/38687324172/job/116265047840); `windows-latest/3.13` [116265047752](https://github.com/ningcol/PACT/actions/runs/38687324172/job/116265047752).
