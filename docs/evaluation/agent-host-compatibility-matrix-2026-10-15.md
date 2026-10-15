# PACT S6 — real Agent / host integration matrix

> **Non-claim**: this document does not assert that Codex, Claude Code or OpenCode has performed an interactive task. Only `ningcol/PACT` and its disposable PACT fixtures are allowed to be modified. No external repository writes, real production credentials or private host CI commands.

## Two different matrices

- **OS × Python engineering portability**: Linux/macOS/Windows × Python 3.11/3.12/3.13, selected test jobs; the PACT source/installed runtime checks have their own evidence.
- **Agent × layer real behavior**: the nine cells **below**; each requires an actual authorized Agent runner, its version/mode and a fresh log. A Python CLI unit test *cannot* mark a cell verified.

| Actual Agent | CLI invocation | Instruction loading | End-to-end Contract→Evidence→Convergence→Owner→finish |
| --- | --- | --- | --- |
| Codex | **blocked** — valid authorized runner required | **blocked** — observed guide loading required | **blocked** — real Agent execution trace required |
| Claude Code | **blocked** — valid authorized runner required | **blocked** — observed guide loading required | **blocked** — real Agent execution trace required |
| OpenCode | **blocked** — valid authorized runner required | **blocked** — observed guide loading required | **blocked** — real Agent execution trace required |

`verified` is allowed only after the test case is truly executed, not after a review request, tool mention, synthetic response or CI's system Python tests. For each verified cell append Runner version/build, model/mode, command, PACT fixture SHA, real transcript/log URI, exit status, Task Contract/Context digests, whether it read the correct guide, and the observed security/semantic result.

## PACT-only reproducible probe, no host CI side effects

For a PACT-owned disposable installed target (never real `ziliu`, `zx-zsb`, or production projects):

```sh
python scripts/pact/init.py --target <PACT_OWNED_TEMP_TARGET> --apply
python <PACT_OWNED_TEMP_TARGET>/pact.py doctor --host-wiring-only --json
python <PACT_OWNED_TEMP_TARGET>/pact.py task prepare "One explicit sandbox requirement" --success "An observable fixture result" --risk medium --json
```

The `doctor --host-wiring-only` command only reads bounded local guide/CI metadata; it does not execute host CI, install host dependencies, or claim Agent compliance. Its `needs-manual-review` means **unknown**, not pass. Avoid using `doctor`'s normal map/check/fitness work when a purely static preflight is intended.

### CLI layer

In a newly created, authorized Agent session, use that Agent's own documented interactive invocation to run `pact.py --help` and `task status <TASK-ID> --json` in a PACT-owned fixture. Capture the **actual Agent version and call/response**, not a generic shell run without the Agent.

### Instruction layer

Place a PACT route inside the isolated target's existing guide **only through a reviewed PACT-owned fixture**, respecting pre-existing `AGENTS.md`, `CLAUDE.md`, and OpenCode settings. Record which host guide the Agent actually loaded. If it did not load the expected guide, classify as **failed**; if loading cannot be observed, keep **unverified**. Never overwrite a real host guide to make the test pass.

### End-to-end layer

Give the real Agent one fixed task with an explicit Task Contract, then observe its choice of Context/Decision/Rule, `task verify` run receipt, Convergence coverage, Owner Report exact Claim bindings and `task finish` gate. Test at least one negative case (stale managed worktree or unverified required AC) as well as a legitimate success path. Do not supply the expected solution diff or oracle until the Agent's run is frozen.

## Preconditions / remaining blockers

1. Authorization for three real Agent runners in strictly **PACT-only** test environments, including their valid mode/version and clean starting session.
2. Logs saved under PACT-owned CI artifacts/PR reports with credential redaction; no private transcript/production data.
3. A separate real Owner observation protocol for S7; Agent behavior alone cannot prove Owner workload improvement.
4. Independent substantive code/plan reviews; earlier Copilot/Codex quota-limited requests do not count.

**Current S6 V classification: blocked (9/9 unverified real sessions)**. The static host/installation engineering E checks can pass separately, but S6 overall and Eight-stage Accepted cannot be reported passed until the nine real Agent cells have actual evidence.
