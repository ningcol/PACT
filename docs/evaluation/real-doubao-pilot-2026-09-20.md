# Real Owner-Project Pilot Baseline — DouBaoFreeImageGen — 2026-09-20

This note records the first machine-observed PACT task lifecycle on an owner-maintained brownfield repository.

It is a **baseline observation**, not a claim that PACT has already reduced owner cognitive load or engineering cost. Human-only dimensions remain unmeasured unless explicitly recorded.

## Reproducible inputs

- Target repository: `ningcol/DouBaoFreeImageGen`
- Target commit: `78aaedd030bc2e24d71e34598326e45cb5cf8127`
- PACT lifecycle validation head: `58bf0168d7ea6155c7d7c050c14a5440c6a74f82`
- Temporary validation PR: #117
- Retrieval fix validated by the pilot: #119
- Follow-up workspace-isolation fix exposed by the pilot: #121
- Task ID: `REAL-DOUBAO-LIFECYCLE-001`
- Risk: `medium`
- Task: `Document round-robin dispatch without changing behavior`

The task intentionally changed only one non-behavioral comment in `McpServer/server.py`. The pilot did not connect to a live Doubao browser client and did not claim external image-generation behavior was verified.

## What the pilot found before completion

The initial lifecycle exposed a real Context retrieval defect:

- `pact inspect` located `McpServer/server.py`;
- medium-risk `task prepare --code` initially produced zero prepared code artifacts.

After #119:

- the original task wording remained the first discovery query;
- `round_robin_index get_idle_client` remained an additional retrieval hypothesis;
- prepared Context included `McpServer/server.py`;
- two browser-proxy files were also selected as code candidates.

The same lifecycle was rerun after the fix and completed successfully.

The run also exposed PACT-owned workspace pollution:

- prepare recorded `.pact/install.json` as pre-dirty control-plane state;
- the run receipt reported `dirty=true` and `untracked_count=1`.

That observation became #120 and was fixed by #121 so install provenance no longer counts as product workspace/task delta.

## Machine-observed task facts

### Context

| Metric | Observed value |
|---|---:|
| Knowledge artifacts | 0 |
| Code artifacts | 3 |
| Known unknowns | 2 |
| Token budget | 40,000 |
| Selected estimated tokens | 13,576 |
| Candidate estimated tokens | 13,576 |
| Dropped candidates | 0 |
| Authority overage tokens | 0 |

Selected code paths included:

- `McpServer/server.py`
- `DoubaoMcpBrowserProxy/background.js`
- `DoubaoMcpBrowserProxy/content.js`

This shows the required implementation file was present. It does **not** establish that every selected candidate was necessary or that the Context was subjectively low-noise.

### Verification

| Metric | Observed value |
|---|---:|
| Verification runs | 1 |
| Passed runs | 1 |
| Failed runs | 0 |
| Runs that changed workspace | 0 |

The verification compiled `McpServer/server.py` and mechanically asserted that the task diff contained exactly one added non-behavioral comment and no deletion.

### Completion integrity

| Metric | Observed value |
|---|---:|
| Completion attempts | 1 |
| Failed completion attempts | 0 |
| Stale-workspace blocks | 0 |
| Stale-Task-Contract blocks | 0 |
| Acceptance-gap blocks | 0 |
| Convergence-coverage blocks | 0 |
| Changed-file-coverage blocks | 0 |
| CI-requirement blocks | 0 |
| Final complete | true |

Acceptance coverage:

- total criteria: 2;
- Evidence verified: 2/2;
- Owner Report covered: 2/2.

Evidence / convergence:

- Evidence claims: 1 pass, 0 fail, 0 unverified;
- execution-backed claims: 1;
- workspace-bound claims: 1;
- CI-metadata claims: 1;
- Convergence findings: 0;
- owner decisions: 0.

Task delta:

- exact changed-file attribution supported: yes;
- changed files: 1;
- path: `McpServer/server.py`;
- Final Impact generated: yes.

## Human-required dimensions that remain unknown

PACT correctly left these fields unfilled rather than fabricating values:

- owner product decisions;
- technical implementation escalations to the owner;
- clarification rounds;
- owner comprehension;
- subjective Context overload;
- PACT-specific overhead minutes.

Because these values were not collected, this pilot cannot establish that PACT reduced owner interruptions, improved comprehension, or paid for its process overhead.

## What this one pilot supports

The evidence supports narrower statements:

1. PACT can be freshly adopted into this pinned brownfield repository without rewriting tracked product files.
2. A remembered feature can be located and carried into a medium-risk prepared Context after the retrieval fix.
3. The task can pass through execution-backed Evidence, Convergence, Owner Report, changed-file coverage, Final Impact, machine evaluation, and upgrade dry-run.
4. A real pilot can expose framework defects that repository-local tests miss: this lifecycle directly drove #119 and #121.

## What it does not support

This single task does not establish:

- that PACT lowers owner cognitive load;
- that PACT is faster than a baseline workflow;
- that 13,576 estimated Context tokens is optimal;
- that the two extra browser-proxy candidates were necessary;
- that PACT improves external Doubao behavior;
- that one successful medium-risk task generalizes to other projects or risk levels.

## Next comparison

The next real-task sample should preserve the same machine observation fields and additionally record the human-required dimensions when feasible.

Useful comparison targets include:

- a task with durable Product Truth / Decisions, so knowledge-artifact convergence is exercised;
- a task that genuinely requires an owner product decision;
- a task where PACT blocks a false completion or stale verification claim;
- a comparable baseline/Pact pair when overhead and owner-interaction measurement is practical.

Do not set a combined PACT score from this sample. Keep the dimensions separate and use multiple real tasks before simplifying or expanding the framework based on evaluation results.
