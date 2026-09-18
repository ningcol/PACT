# PACT Brownfield Initialization Checklist

Use this checklist to adopt PACT in an existing repository without trying to document the entire past.

## 0. Create a reviewable adoption point

- [ ] clean or isolated branch/worktree;
- [ ] current build/test status recorded;
- [ ] no unrelated refactor bundled into PACT adoption.

## 1. Observe repository reality

- [ ] identify major modules/domains;
- [ ] identify runtime entry points;
- [ ] identify API/schema/contract sources;
- [ ] identify build/test/CI entry points;
- [ ] identify existing docs and agent instructions;
- [ ] identify obvious stale/conflicting docs.

Output: observed facts only.

## 2. Establish vocabulary

For each important business concept:

- [ ] canonical owner-facing name;
- [ ] precise meaning;
- [ ] code/data aliases;
- [ ] historical aliases;
- [ ] confusing near-synonyms.

Do **not** mass-rename old code as part of initialization.

## 3. Establish Product Truth baseline

Select only high-value rules:

- [ ] long-lived;
- [ ] cross-module or cross-page;
- [ ] expensive to violate;
- [ ] easy for agents to misunderstand;
- [ ] backed by an authoritative source or explicit owner confirmation.

Rules inferred only from code remain candidates/observations.

## 4. Establish current Architecture baseline

- [ ] main modules and dependency direction;
- [ ] data ownership;
- [ ] state ownership;
- [ ] public/API boundaries;
- [ ] auth/security boundaries;
- [ ] infrastructure boundaries;
- [ ] important current invariants.

Describe current structure, not the whole history.

## 5. Backfill only durable decisions still relevant

Consider:

- [ ] auth model;
- [ ] data ownership;
- [ ] API layering;
- [ ] state ownership;
- [ ] deployment model;
- [ ] persistence strategy;
- [ ] important rejected alternatives likely to recur.

Do not reconstruct decisions that no longer matter.

## 6. Declare authority

- [ ] product meaning authority;
- [ ] runtime/current behavior authority;
- [ ] contract/schema authority;
- [ ] current architecture authority;
- [ ] durable rationale authority;
- [ ] current change intent authority;
- [ ] verification/evidence authority.

## 7. Configure owner interface

- [ ] canonical business language;
- [ ] technical details hidden by default;
- [ ] consequence-first explanation;
- [ ] escalation limited to product/risk decisions;
- [ ] preferred completion-report style.

## 8. Record verification reality

- [ ] build;
- [ ] unit/integration tests;
- [ ] browser/E2E;
- [ ] visual checks;
- [ ] schema/contract checks;
- [ ] CI gates.

Mark missing capabilities as missing. Do not pretend they exist.

## 9. Register known drift

For each important unresolved conflict:

- [ ] give it a Drift ID;
- [ ] state the conflict;
- [ ] state temporary authority treatment;
- [ ] state severity;
- [ ] state revisit condition.

## 10. Run readiness review

PACT is ready when a new agent can answer, with reasonable confidence:

1. What does this business concept mean?
2. Where are its durable rules?
3. What does the system currently do?
4. Why does the current architecture work this way?
5. Which decisions can the agent make autonomously?
6. What must be verified before claiming completion?
7. How should unresolved product ambiguity be presented to the owner?

## Exit criteria

Initialization is complete enough when future work can proceed safely. It is **not** required to eliminate all historical drift or document every feature.
