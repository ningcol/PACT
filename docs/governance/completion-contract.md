# Completion Contract

PACT treats "done" as an evidence-backed claim.

## Task Contract

A prepared task has a machine-readable Task Contract containing:

- the task intent;
- observable acceptance criteria with stable `AC-*` IDs;
- explicit constraints that must remain true.

Evidence claims may bind to one or more acceptance IDs. Prepared Task Contracts are fingerprinted, and completion requires Evidence to carry the SHA256 of the exact contract it verified. When a Task Contract is present, completion fails if the contract changed after verification, if any acceptance criterion lacks passing Evidence, or if that Evidence is not represented in the Owner Report.

Task Contract intent is task-scoped authority. It does not silently override confirmed durable Product Truth; conflicts require reconciliation or an owner-level product decision.

## Task Context and Convergence

A high-level prepared task also fingerprints its Task Context.

Completion requires the Convergence Report to:

- bind to the exact prepared Context SHA;
- explicitly cover every selected knowledge artifact;
- state whether each artifact is aligned, updated, stale, owner-decision, or not applicable;
- avoid claiming `updated` when the prepared artifact fingerprint proves the file did not change.

This prevents relevant project knowledge from disappearing between implementation and completion. It does not ask PACT to infer semantic truth from arbitrary prose; the Agent still performs the semantic classification, but omission becomes mechanically visible.


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
