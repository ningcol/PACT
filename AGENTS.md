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
- Drift lifecycle: `docs/drift/`
- Reusable procedures: `.agents/skills/`
- Adoption baseline/readiness: `.pact/baseline.toml`
- System design: `docs/design/system-overview.md`

## Default Agent Surface

Prefer the small task-oriented interface when it is sufficient:

```bash
python3 pact.py status
python3 pact.py inspect "<remembered feature/business behavior>"
python3 pact.py task prepare "<task>" --success "<observable outcome>" --risk <level>
# Add repeatable --accept / --constraint when the task has multiple explicit conditions.
python3 pact.py task finish <TASK-ID>
```

These are default orchestration helpers, not mandatory workflow steps. Use lower-level `discover/context/impact/run/evidence/converge/report/complete` primitives directly when that is more efficient or precise. Never bypass truth/evidence requirements merely to reduce steps.

## Before changing behavior

Determine the affected product/domain scope and retrieve only the relevant rules, architecture, decisions, code, tests, and history needed for high confidence.

Do not infer product truth from code alone.

If `pact readiness` reports a baseline area as pending, treat that area as incomplete/unknown rather than manufacturing missing truth.

## Decision policy

Do not ask the owner to choose implementation patterns, classes, state mechanisms, cache strategies, or other internal engineering choices.

Escalate only when the decision changes product meaning, user-observable behavior, data meaning, permissions/policy, irreversible outcomes, or material risk/cost.

## Completion

A task is not done merely because code was written or tests are green.

Done requires, as applicable:

- implementation complete;
- every Task Contract acceptance criterion verified and owner-visible;
- observable behavior verified;
- relevant truth converged;
- no unresolved blocking ambiguity;
- evidence exists for completion claims.

## Communication

Before owner-facing explanations, decisions, or completion reports, load the validated Owner Profile:

```bash
python scripts/pact/pact.py owner --json
```

Honor its language, technical depth, consequence-first decision translation, and progressive-disclosure preferences. These preferences affect communication, not internal engineering capability.

Owner-facing output should answer:

- What changed for the user/business?
- What was actually verified?
- Is project consistency healthy?
- Is there any product decision the owner must make?

Keep implementation details behind progressive disclosure unless requested.
