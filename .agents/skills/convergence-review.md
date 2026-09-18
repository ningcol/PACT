# Skill: Convergence Review

## Purpose

Perform a semantic consistency review after meaningful changes.

This skill reviews; it does not silently redefine product truth.

## Inputs

Use the task/change intent, relevant Product Truth, current architecture, implementation, tests, runtime/browser evidence, and durable decisions needed for the affected scope.

Do not expand to the entire repository unless risk or uncertainty requires it.

## Questions

1. Does observed behavior align with confirmed product truth?
2. Does implementation align with active change intent/spec?
3. Do tests align with the intended product behavior?
4. Does current architecture documentation still match relevant structure?
5. Did the change introduce unrequested behavior?
6. Was a durable engineering decision introduced without a record?
7. Was an existing decision effectively superseded?
8. Is relevant documentation stale?
9. Is there unresolved product ambiguity requiring owner input?

## Classification

- `aligned` — checked and consistent.
- `stale` — technical/current-state documentation needs repair.
- `missing` — required behavior/artifact is absent.
- `partial` — intent is implemented only partly.
- `contradicts` — implementation and authoritative intent conflict.
- `unrequested` — behavior was added without supported intent.
- `owner-decision` — ambiguity is genuinely product/risk-level.

## Task Context coverage

When the task was prepared through `pact task prepare`, the Convergence Report must bind to that exact Task Context and explicitly dispose every selected knowledge artifact.

For each entry in `context.artifacts`, emit one `coverage` item:

- `aligned` — reviewed and still correct;
- `updated` — changed during this task so current project knowledge matches the implementation;
- `stale` — known current-state drift remains and must be visible;
- `owner-decision` — the artifact cannot converge without a genuine product/risk decision;
- `not-applicable` — the artifact was retrieved but is not affected by this change.

Every item requires a concrete rationale. Do not omit an artifact merely because no finding was discovered.

`updated` is mechanically checked when the prepared Context captured an artifact SHA: the current artifact must actually differ (or have been removed). This does not prove semantic correctness, but prevents a no-op file from being reported as updated.

An `owner-decision` coverage item must be accompanied by an `owner-decision` finding containing the owner-facing question.

## Output contract

For a durable or machine-consumed review, emit a JSON report conforming to:

`.pact/schema/convergence-report.schema.json`

Every nontrivial finding must state:

- what was observed;
- what was expected;
- which authority establishes the expectation;
- concrete evidence;
- recommended action.

An `owner-decision` finding must additionally include `owner_question` phrased as an observable product/business choice.

Validate the report with:

```bash
python scripts/pact/converge.py <report.json>
```

## Escalation

Technical drift should normally be repaired autonomously.

Only `owner-decision` findings should interrupt the owner.

Do not turn raw implementation alternatives into owner questions. Translate them into user/business consequences.

## Completion interaction

`missing`, `partial`, `contradicts`, and `owner-decision` are blocking by default.

`stale` may remain nonblocking only when risk is acceptable and the drift is explicitly repaired or registered.
