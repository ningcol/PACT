
# M0 decision-memory A/B — frozen installed-runtime findings

Date: 2026-10-17. Baseline main: `1192363a1539ee77d5819a9cee6d9df64fb1fe17`.

**Nature of evidence:** Seven **fictional**, developer-authored cases.
PACT's real *installed compact runtime* was invoked, but **no independent
Agent executed a task, no authentic Owner consent was observed, and the
developer wrote both input corpus and oracle**. This is not an independent
blind/real-agent effect experiment, nor is the A/B difference causal evidence
of Agent benefit.

## Pre-registration and reproducibility

[Pre-registration](decision-memory-m0-ab-preregistration-2026-10-17.md)
and [frozen inputs](../../benchmarks/decision-memory/m0-inputs.json) /
[synthetic oracle](../../benchmarks/decision-memory/m0-oracle.json)
were committed at `5d5b5ebda1ee49fd3f0897d47e472cf30f27d197`
before the runner was created.

Run:
```bash
python scripts/benchmark/decision_memory_m0.py
```

Evidence: PACT Check [#39004993344](https://github.com/ningcol/PACT/actions/runs/39004993344)
ran the pre-frozen A/B runner on installed `pact.py`, printed every case's
A/B hits, misses and incremental costs, and **PASSED** its instrumentation
and safety checks. The raw runner JSON is emitted by the command; CI printed
its case-level projection. No generated data were copied into a real
downstream project.

Fixed common configuration: `--intent work --no-code --risk low --limit 4
--token-budget 2048`. Arm A used task text alone; arm B received the
**caller-known** Decision ID through existing extra `--query` arguments,
with task text kept primary. Both used the identical source/budget.

## Raw case results

| Frozen case | A target found | B target found | B−A estimated selected tokens | B−A Context elapsed ms |
|---|---:|---:|---:|---:|
| `cache-lexical` | yes | yes | +0 | +304.816 |
| `code-path-vocabulary-gap` | yes | yes | +0 | +303.979 |
| `pathless-vocabulary-gap` | no | yes | +84 | +306.530 |
| `stale-path-after-move` | no | yes | +93 | +304.726 |
| `partial-supersession` | yes | yes | +0 | +299.554 |
| `rejected-alternative` | yes | yes | +0 | +311.731 |
| `unrelated-task` | n/a | n/a | +0 | -16.924 |

**Decision recall across six target-positive synthetic cases:**
A = **4/6 (66.7%)**; B = **6/6 (100%)**. The unrelated seventh case had no
oracle Decision and both arms injected **zero current Decisions**.
No rejected/superseded Decision was promoted to `applicable_rules` or
current `decisions`. The evaluator's **synthetic engineering gate: PASS**
with zero instrumentation failures; this does **NOT** imply A's recall is
sufficient or that the framework prevents real Agent drift.

B's six hinted-case extra Context wall-time: **mean 305.2 ms,
median 304.8 ms** on this CI run. B's extra selected-document
token estimates were 0 in four cases, +84 and +93 where A missed.
These are subprocess timings and crude file-size/4 token estimates,
**not model-token use**, generalized latency/SLA, or Agent runtime overhead.

## Case-specific interpretations and limits

1. **Cache lexical:** A already found the current Decision. Additional hint
   had no recall benefit.
2. **Code path / vocabulary:** A found `DEC-BROKER-EDGE` even though current
   lexical scoring does not implement deterministic `paths` matching.
   This is an incidental lexical hit, **not evidence that path anchors work**.
3. **Pathless / vocabulary-disjoint:** A omitted `DEC-FLUX-CHANNEL`. B
   recovered it because the caller was handed its exact ID. If a new Agent
   does not know that ID, B provides no remedy.
4. **Stale path after rename:** A omitted `DEC-PAYLOAD-ANCHOR` for a new
   location; `paths` still contains missing `src/account/legacy_bridge.py`.
   B retrieved by known ID. No automatic path migration or persistent
   rename repair has occurred.
5. **Partial supersession:** The current implemented `DEC-REPLAY-CURRENT`
   is found. The older `DEC-REPLAY-OLD` remains valid history. This
   benchmark **does not** establish which natural-language constraints still
   bind after a partial replacement.
6. **Rejected alternative:** Historical rejection remains retrievable
   evidence; a rejected Decision cannot become an automatically confirmed
   Product Rule or perpetual prohibition.
7. **Unrelated task:** No current Decision materialized; routine work has
   no synthetic memory-pressure regression.

The current Context Envelope remains `candidate`: selecting a Decision
ID is **not** proof an Agent read, understood, or respected its source
rationale. A summary of selected paths is not a semantic decision audit.

## Evidence-based A/B/C decision

- **A-only blanket rollout: NO-GO for reliable unknown-decision recall**
  in this frozen synthetic set (2/6 misses). Do not reinterpret an empty
  search as no existing constraint.
- **B opt-in: mechanically viable for known explicit IDs**, 6/6 here.
  It does not solve new-Agent discovery of unknown IDs, and this
  particular multi-query path adds measured subprocess overhead even
  when A already succeeds. No new required-Decision CLI introduced.
- **C default automatic graph/path scanner: NOT AUTHORIZED by this data.**
  Two synthetic misses justify targeted investigation and perhaps
  explicit `paths` validation / rename diagnostics, but not yet a new
  broad default mechanism or Owner approval infrastructure.
- **Real Agent/Owner outcome: HOLD/UNVERIFIED.** There is no independent
  unseen oracle, real new-session Agent, matched controls or actual
  Owner observation. Preserve the existing S0 real-pilot NO-GO gates
  without calling them satisfied.

**Next smallest justified step:** test a *PACT-only* bounded path-rename
anchor diagnostic and a cold-start Agent procedure in a fresh environment,
then measure whether either helps without adding false constraints or
long-term notes. If an authorized independent Agent runner/custodian remains
unavailable, keep the real-benefit gate open instead of substituting
synthetic results.

No tag/release; no files in other repositories were edited.
