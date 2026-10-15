+++
[pact]
type = "decision"
id = "DEC-EXAMPLE-001"
status = "proposed"
owners = ["engineering"]
domains = []
related = []
supersedes = []
+++

# Decision: <title>

## Problem

What durable problem are we solving?

## Decision

What are we choosing?

## Rejected alternative evidence (only when status is rejected)

Record the real alternative, why it was tempting, what evidence contradicted
it (distinguish observed / owner-confirmed / assumed), the **scope and premises
that made rejection valid**, and what would justify reconsidering it. Omit
invented experiments; no special metadata field is required.

## Alternatives considered

Only include alternatives that were actually considered. Do not invent fake debate to satisfy the template.

## Consequences

What do we gain, and what cost/constraint do we accept?

## Invariants

What must future implementations preserve?

## Verification

How can a future agent verify that the decision still holds?

## Revisit conditions

Reconsider this decision when:

- ...

## Related decisions

- ...

## Supersedes / superseded by

- Link actual Decision IDs and repository-relative paths.
- If partial: name which earlier constraints **remain in force** and where
  future agents can find them; do not simply mark all old rationale obsolete.
- If full: show the new location of inherited invariants and risks; keep an
  outbound historical link from the superseded record.
