# Completion Contract

PACT treats "done" as an evidence-backed claim.

## Task Contract

A prepared task has a machine-readable Task Contract containing:

- the task intent;
- observable acceptance criteria with stable `AC-*` IDs;
- explicit constraints that must remain true.

Evidence claims may bind to one or more acceptance IDs. Prepared Task Contracts are fingerprinted, and completion requires Evidence to carry the SHA256 of the exact contract it verified. When a Task Contract is present, completion fails if the contract changed after verification, if any acceptance criterion lacks passing Evidence, or if that Evidence is not represented in the Owner Report.

Task Contract intent is task-scoped authority. It does not silently override confirmed durable Product Truth; conflicts require reconciliation or an owner-level product decision.

## Optional mechanical completion helpers

`task draft <TASK-ID>` writes schema-shaped, explicitly **incomplete**
Evidence/Convergence/Owner Report files inside a repository-owned completion
bundle. It never overwrites an existing file, and refuses corrupt Evidence.
The draft Convergence has a blocking `partial` finding and no automatic
knowledge/change coverage; the draft Owner Report is `partial`, not completed.

`task verify <TASK-ID> --criterion AC-1 --claim "..."` runs a concrete command
through `pact run` and records its real exit status and workspace-bound receipt
against an **explicitly chosen** criterion. It does not infer that the command
proves the product outcome, it does not mark all criteria passed, and it cannot
write to an external completion bundle. Failed checks are retained as failed
Evidence rather than being rewritten as success. Manual review of the
Evidence-to-outcome relationship, Convergence and Owner Report is still
required. Existing advanced primitives remain available.

## Task state preflight and repository boundaries

High-level prepared task state is repository-owned. Before preparation or task-backed reads/writes, PACT checks that its `.pact/tasks` root (and its `.pact` ancestor) does not traverse a symlink, a non-directory component, or a path outside the repository. `task prepare` additionally checks `.pact/completions` and `.pact/tmp`. Default completion state in `task finish` and `task status` is subject to the same root boundary. Explicit custom completion bundles remain supported according to their existing CLI contract.

At `task finish`, the recorded Task Contract and Task Context must both exist inside the repository and match the prepared SHA256 values **before** the changed-file set is derived, Final Impact is generated, or `task.json` and attempt-history state is updated. An invalid Context is a preflight error (exit 2), not a completed validation attempt (exit 1), and has no task-completion-side-effect writes. Normal failed Evidence/Convergence acceptance still creates an auditable failed completion attempt after successful preflight.

`task status` and contract-backed `eval --task` reject these invalid prepared paths and digests. Legacy minimal evaluation observations without a prepared Task Contract remain readable. Filesystem validation is not a lock: a concurrent noncooperating writer can still race with a later read or write. PACT does not claim signed or tamper-proof local state.

## Completion Bundle path and retry consistency

A prepared Task Manifest records its completion-bundle location. The default location is `.pact/completions/<TASK-ID>`; `task finish --bundle PATH` may select an alternative relative or absolute location under the existing custom-bundle contract. When successful completion records that location in the Manifest, a later `task finish TASK-ID` without another `--bundle` **reuses the saved path**, consistent with `task status` and task evaluation. A later explicit `--bundle` overrides the saved selection and becomes the new saved default on success.

If `completion_bundle` is absent, the original default location is used. If explicitly stored as an invalid value (including `null`, non-string, or empty string), the saved-path operation fails before completion side effects. The repository-owned default completion root still receives the state-root confinement checks; explicitly selected custom/absolute paths keep their previously supported behavior.

## Task Context and Convergence

A high-level prepared task also fingerprints its Task Context.

Completion requires the Convergence Report to:

- bind to the exact prepared Context SHA;
- explicitly cover every selected knowledge artifact;
- state whether each artifact is aligned, updated, stale, owner-decision, or not applicable;
- avoid claiming `updated` when the prepared artifact fingerprint proves the file did not change.

This prevents relevant project knowledge from disappearing between implementation and completion. It does not ask PACT to infer semantic truth from arbitrary prose; the Agent still performs the semantic classification, but omission becomes mechanically visible.


## Run process and output-pipe completeness

`pact run` streams a direct verification child's stdout and stderr into SHA256 digests without persisting raw output. Successful execution requires the command to exit successfully **and** both streams to reach EOF, so the digests represent complete output.

When a direct child spawns a descendant that inherits either output pipe, closing only the direct child does not necessarily close the pipes. After the direct child exits, PACT uses one bounded 3-second drain deadline for both reader threads. If either pipe remains open at that point, PACT reports an execution error and **does not publish a run receipt**, even if the direct command returned exit code zero. Short-lived descendants that close the pipes within the deadline remain supported.

When only PACT itself receives a keyboard interrupt, it requests termination of the direct child (escalating to kill after a 2-second grace period), bounds the subsequent output reader waits, returns exit code 130, and does not publish a new receipt when cleanup succeeds. As before, OS-level uninterruptible direct-child reaping is not given a strict deadline. PACT does not attempt portable termination of arbitrary descendant process trees. A noncooperating descendant may outlive PACT, and its cleanup belongs to the calling environment. This is a fail-closed evidence boundary, not a guarantee of full process-tree cleanup.

## Git worktree fingerprint and submodule boundary

PACT binds execution-backed Evidence to a Git worktree snapshot. For tracked files, the snapshot includes staged index state, unstaged content and Git file type/execute-bit semantics; it separately accounts for visible untracked files. Git -z path identities are preserved, including a literal backslash in a POSIX filename.

Tracked Git submodules are supported when initialized, at the exact commit staged in the parent index, and recursively clean. A dirty, moved, uninitialized, or uninspectable submodule fails snapshot/baseline/attribution rather than claiming that two potentially different worktrees have the same verification identity. This deliberate fail-closed policy does not imply that all ignored, remote, environment-based, or otherwise external verification inputs are covered.

Git fingerprint V3 intentionally invalidates previously recorded V2 `pact run` workspace hashes. A pending task with older run receipts must rerun verification before a trustworthy completion claim; pre-V3 *task preparation* dirty-file state encodings are normalized for changed-file attribution, not elevated into new execution evidence.

## Actual changed-file coverage

For a prepared task in a Git worktree, PACT records the prepare-time Git HEAD plus the content state of paths that were already dirty before the task. It does **not** require a clean workspace.

At `task finish`, PACT derives the paths whose final content differs from that prepared baseline. This includes uncommitted and committed additions, modifications, and deletions while excluding generated/installed PACT control-plane state such as local task/run/cache state and `.pact/install.json`. Project-owned seed files re-enter project state once customized.

Completion then:

- generates a final Impact report from those actual task-changed paths;
- requires `convergence.change_coverage` to contain every task-changed path exactly once;
- rejects missing, duplicate, or stale/extra path coverage;
- leaves pre-existing dirty files alone when their content did not change during the task.

Each change-coverage entry contains a path and an Agent-written rationale. PACT checks coverage mechanically; the rationale remains semantic review.

For non-Git projects, PACT reports that exact task-delta path attribution is unavailable rather than inventing changed-file coverage.

## Mechanical integrity versus semantic assertion

PACT deliberately separates two trust layers:

- **mechanical integrity** — task IDs, schema, hashes, prepared risk, exact workspace binding, exit-status consistency, changed-file coverage, and Evidence references;
- **semantic assertion** — whether a particular test/runtime command truly proves the business claim an Agent attaches to it.

A local `pact-run` receipt is an execution-backed, workspace-bound provenance record. It is **not** a tamper-proof machine attestation. PACT can validate the receipt's structure and consistency, but an independent remote/signed attestation is required when the threat model includes a party rewriting local control-plane files.

Owner Report verification text must not broaden a passing Evidence claim. Business-friendly consequence summaries belong in `summary`, `before`, and `after`; the machine-checked verification entry stays bounded by its referenced Evidence.

## Default definition

A task is complete when, to a degree appropriate for its risk:

1. implementation is complete;
2. observable behavior is verified;
3. relevant project truth has converged;
4. no blocking ambiguity remains;
5. required evidence exists.

## Risk-adaptive rigor

### Low risk

Examples: text, spacing, obvious local bug.

Expected: targeted inspection and verification.

### Medium risk

Examples: normal feature, cross-component state, ordinary API behavior.

Expected: affected feature context, relevant tests, observable verification, targeted convergence.

### High risk

Examples: permissions, migration, schema, public contract, security, payments, cross-domain rules.

Expected: deeper context, durable decisions where applicable, stronger verification, convergence, and durable evidence when justified.

## Invalid completion claims

Do not report:

- "verified" when no verification was run;
- "no impact" without checking affected behavior;
- "safe" based only on code inspection;
- "tests pass" when tests were not executed;
- "matches product requirements" when product truth was never located.

When something could not be verified, say so explicitly.
