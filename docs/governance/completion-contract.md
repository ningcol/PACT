# Completion Contract

PACT treats "done" as an evidence-backed claim.

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
