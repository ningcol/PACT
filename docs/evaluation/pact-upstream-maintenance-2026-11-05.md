# PACT completion cost and maintenance boundaries: engineering evaluation

Date: 2026-11-05. Baseline commit: `650888787b550f9df1e5a13720a3cd87b81e4499`.
Task: `PACT-UPSTREAM-20261105`, with sixteen acceptance criteria prepared before
implementation. This report concerns upstream PACT; no gaokao_zx files or installed
runtime were changed.

## Attribution and scope

PACT owns the cost of its Git attribution, completion diagnostics, retrieval,
task generations and installed runtime identity. Project-specific business tests,
release procedures, custom documentation locations and owner policies retain
their own authority. This change does not establish how much of a real project's
total session time is attributable to each source.

The implementation preserves workspace-bound receipts and explicit convergence
review. It does not reuse stale execution evidence, treat a passing record check
as business verification, or require another mandatory workflow or knowledge
record. Knowledge retention still permits `none` and updates to existing homes.

## Repeated synthetic performance comparison

Command:

```bash
python3 -B scripts/benchmark/workspace_batch.py --files 350 --repeats 3
```

The script loads the pinned baseline implementation from Git and the current
implementation into separate modules. Both operate on the same disposable
synthetic repository, including prepared dirty files, an intervening commit,
staged changes and subsequent unstaged changes. Every returned object must match;
any difference fails the command. Git invocation counts include the operation's
Git subprocesses, not repository setup. Timings are local elapsed times under
concurrent engineering work, not a universal latency promise.

| Operation | Before median | After median | Git calls before / after |
| --- | ---: | ---: | ---: |
| Workspace snapshot | 9.352 s | 0.342 s | 271 / 9 |
| Task changed-file attribution | 40.298 s | 0.596 s | 973 / 12 |

All three comparisons per operation returned exactly equal results, including
the existing V3 snapshot identity. The current `workspace.py` SHA256 was
`1efb824eb665dd0b54879e12e8e427cedb5469d10478e9bce1705c90c7aa28d2`.
An earlier 400-file single run also matched: 13.941 / 0.445 s and 308 / 9 Git
calls for snapshots; 55.015 / 0.552 s and 1109 / 12 for attribution.

These measurements concern PACT's read-only attribution, not business test time,
documentation review time or a measured end-to-end gaokao_zx session improvement.

## Review rounds and resolved findings

1. Implementers added subsystem regressions; another implementer reviewed each
   affected subsystem. Review found that malformed historical manifests could
   be archived successfully but become unreadable later. Staging and reading now
   share identity/status/baseline validation, with negative and rollback tests.
2. Completion review found that repeating full Claim details under every AC
   could create excessive diagnostics. Claims are now emitted once, with bounded
   text/references, bounded AC links and an explicit truncation indicator.
3. Retrieval review found that an initial discovery result could hide a final
   Change-only selection after materialization budgets. Diagnostics now examine
   selected Context, with a regression for this budget boundary.
4. A fresh independent reviewer inspected the integrated implementation and ran
   additional real-Git differential checks in eight temporary repositories
   (sixteen assertions). No confirmed blocking defect remained in that review.

The first development-wide test run loaded an earlier, still-changing test
version and failed on a non-UTF-8 filename rejected by this macOS filesystem.
The final test version separates that filesystem-specific case and explicitly
skips it when unsupported. Its final targeted run was ten tests, nine passes and
one skip. This limitation is not evidence that unsupported filenames were tested.

## Installed independent replay

`scripts/pact/tests/test_installed_maintenance_replay.py` preserves the fresh
reviewer's installed replay as executable behavior assertions. Ten actual CLI
calls install a temporary project, initialize Git, retrieve a long Chinese
question containing the registered alias `交付留存`, prepare Context, upgrade and
inspect `doctor`.

Assertions check confirmed Domain/Rule retrieval, candidate status preserved in
navigation but excluded from `applicable_rules`, unchanged candidate source
bytes, unchanged customized AGENTS/config after upgrade, and runtime version,
archive SHA256, integrity and supported capabilities. The targeted replay passed.

Its authority is an explicitly synthetic fixture Owner specification. It is an
independent engineering replay, not a blinded Agent/Owner study, real user
approval or evidence of long-term behavior improvement.

## Final acceptance evidence

Final checks must execute on the integrated worktree through `pact task verify`:
the required help/schema/workflow/check gates, the full unittest suite, the
synthetic baseline comparison and the installed replay. Their actual commands,
exit status, workspace identity and Claim-to-AC links belong in
`.pact/completions/PACT-UPSTREAM-20261105/evidence.json` and its referenced run
receipts. Final semantic review belongs in that bundle's Convergence and Owner
Report; `task finish --require-knowledge-retention` is the completion gate.

Local task bundles are ignored generated state, not distributed project truth.
This document records measured results and review limitations without claiming
that existence of a report or receipt proves business correctness.
