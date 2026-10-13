# Convergence Model

Convergence asks:

> After implementation, do actual project artifacts still agree with the authoritative desired state?

It is not simple document synchronization.

## 1. Review targets

A meaningful change may require checking:

- Product Truth ↔ observed behavior;
- active change/spec ↔ implementation;
- tests ↔ intended behavior;
- architecture docs ↔ current structure;
- contracts/schema ↔ public behavior;
- accepted design ↔ rendered UI;
- agent guidance ↔ repository reality;
- durable decisions ↔ shipped architecture.

## 2. Finding classes

- `aligned` — checked and consistent.
- `stale` — current-state technical documentation needs repair.
- `missing` — intended behavior/artifact is absent.
- `partial` — intent is implemented only partly.
- `contradicts` — actual state conflicts with authoritative intent.
- `unrequested` — behavior exists without supported intent.
- `owner-decision` — authority is genuinely ambiguous at the product/risk level.

## 3. Who resolves what

Technical drift:
- normally repaired autonomously by AI.

Product ambiguity:
- escalated through Decision Translation.

Generated drift:
- regenerate the artifact.

Machine-enforceable invariant drift:
- fail the deterministic gate.

## 4. Coverage before findings

A finding list answers:

> What inconsistency did the reviewer notice?

It does **not** prove that the reviewer looked at every relevant knowledge artifact.

For a prepared task, PACT therefore binds semantic Convergence to the exact Task Context:

```text
Task Context SHA256
        ↓
Convergence.context_sha256

Task Context artifacts
        ↓
Convergence.coverage[]
```

Every knowledge artifact selected into the task Context needs one explicit disposition:

- `aligned`;
- `updated`;
- `removed`;
- `stale`;
- `owner-decision`;
- `not-applicable`.

This is a coverage guarantee, not a semantic oracle. PACT can prove that `README.md` was not silently omitted; it cannot mechanically prove that an Agent was correct to call the README aligned.

Prepared Context artifacts also carry their content SHA when available. The dispositions have distinct filesystem requirements:

- `updated`: the artifact must still be a regular file, and its current SHA256 must differ from the prepared SHA256. Missing prepared hashes cannot prove an update.
- `removed`: the artifact must have had a prepared content SHA256 and must now be absent. A recreated file, directory or symlink at that path is not a verified removal.
- `aligned`, `stale` and `not-applicable`: none can excuse a missing prepared artifact. A missing artifact requires `removed` or a blocking `owner-decision` review.
- `owner-decision`: when authority to delete is unsettled, an `owner-decision` finding containing an owner question blocks completion.

A `removed` coverage entry must use its required `rationale` to cite the governing intent or decision authorizing the deletion; it is **not** a mechanism for overriding Product Truth. PACT checks prepared SHA and the current path state, but cannot mechanically prove authorization, distinguish intentional deletion from accidental deletion, or validate the reviewer's semantic judgment. Without adequate authority, restore the artifact or record a blocking owner decision.

Legacy reports that called a now-absent artifact `updated` will fail the new mechanical check and must be reviewed again. The schema change is an additive `removed` enum value; existing valid reports for present artifacts remain valid.

## 5. Structured reviewer output

Semantic reviewers should emit a Convergence Report conforming to:

`.pact/schema/convergence-report.schema.json`

This makes LLM judgment inspectable without pretending the judgment itself is deterministic.

## 6. Owner boundary

A finding may interrupt the owner only when classified `owner-decision`.

The report must describe:

- observable consequence;
- evidence for the conflict;
- the exact product/risk question that needs owner input.

Raw technical alternatives are not sufficient.

## 7. Done boundary

A task should not be called complete if the report contains unresolved blocking:

- `missing`;
- `partial`;
- `contradicts`;
- `owner-decision`.

Severity and task context determine whether non-blocking stale findings may remain registered as known drift.
