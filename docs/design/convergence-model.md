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

## 4. Structured reviewer output

Semantic reviewers should emit a Convergence Report conforming to:

`.pact/schema/convergence-report.schema.json`

This makes LLM judgment inspectable without pretending the judgment itself is deterministic.

## 5. Owner boundary

A finding may interrupt the owner only when classified `owner-decision`.

The report must describe:

- observable consequence;
- evidence for the conflict;
- the exact product/risk question that needs owner input.

Raw technical alternatives are not sufficient.

## 6. Done boundary

A task should not be called complete if the report contains unresolved blocking:

- `missing`;
- `partial`;
- `contradicts`;
- `owner-decision`.

Severity and task context determine whether non-blocking stale findings may remain registered as known drift.
