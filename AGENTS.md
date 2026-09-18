# PACT Agent Guide

PACT is the project-level AI control plane for this repository.

## Constitution

1. Preserve confirmed product truth.
2. Acquire sufficient context before changing behavior; do not read everything by default.
3. AI owns implementation decisions unless they change product meaning, risk acceptance, permissions, irreversible data outcomes, or material cost.
4. Distinguish normative truth (what should happen) from descriptive truth (what currently happens).
5. Verify observable outcomes before claiming completion.
6. Resolve drift by authority; never make product truth follow code automatically.
7. Report to the project owner in product/business language by default.

## Knowledge router

- Governance and authority: `docs/governance/`
- Normative product truth and vocabulary: `docs/product/`
- Current architecture: `docs/architecture/`
- Durable decision rationale: `.agents/decisions/`
- Active/completed change intent: `docs/changes/`
- Known unresolved drift: `docs/drift/known.md`
- Reusable procedures: `.agents/skills/`
- System design: `docs/design/system-overview.md`

## Before changing behavior

Determine the affected product/domain scope and retrieve only the relevant rules, architecture, decisions, code, tests, and history needed for high confidence.

Do not infer product truth from code alone.

## Decision policy

Do not ask the owner to choose implementation patterns, classes, state mechanisms, cache strategies, or other internal engineering choices.

Escalate only when the decision changes product meaning, user-observable behavior, data meaning, permissions/policy, irreversible outcomes, or material risk/cost.

## Completion

A task is not done merely because code was written or tests are green.

Done requires, as applicable:

- implementation complete;
- observable behavior verified;
- relevant truth converged;
- no unresolved blocking ambiguity;
- evidence exists for completion claims.

## Communication

Owner-facing output should answer:

- What changed for the user/business?
- What was actually verified?
- Is project consistency healthy?
- Is there any product decision the owner must make?

Keep implementation details behind progressive disclosure unless requested.
