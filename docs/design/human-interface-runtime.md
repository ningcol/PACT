# Human Interface Runtime

The Human Interface layer is not a writing-style prompt. It is a contract between engineering evidence and owner-facing communication.

## 1. Inputs

An owner-facing completion report should be grounded in:

- the requested product outcome;
- Evidence Receipt;
- Convergence Report;
- canonical business vocabulary.

## 2. Owner Report

A structured Owner Report conforming to:

`.pact/schema/owner-report.schema.json`

contains:

- outcome status;
- concise owner summary;
- before/after product behavior;
- verification claims linked to Evidence IDs;
- project consistency summary;
- owner decisions, if any;
- optional technical detail references.

## 3. Evidence binding

Every verification statement in the Owner Report must reference an Evidence ID present in the Evidence Receipt.

PACT tooling cross-checks those references.

An owner report cannot truthfully say "completed" when:

- required evidence is failed/unverified; or
- convergence still requires reconciliation/owner input.

## 4. Decision translation

Owner decisions describe consequences, not raw technical options.

Each option should tell the owner what changes for users/business/data/risk.

## 5. Progressive disclosure

Default owner view:

1. result;
2. product/user change;
3. verified scenarios;
4. consistency state;
5. any required owner decision.

Technical files/symbols/details stay optional.

## 6. Why this is separate from agent execution

Agents remain free to use precise engineering language internally.

The Human Interface layer protects owner cognition without reducing engineering precision.
