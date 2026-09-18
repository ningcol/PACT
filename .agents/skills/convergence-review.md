# Skill: Convergence Review

## Purpose

Perform a semantic consistency review after meaningful changes.

This skill reviews; it does not silently redefine product truth.

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

- `aligned` — no action.
- `stale` — technical/current-state documentation needs repair.
- `missing` — required behavior/artifact is absent.
- `partial` — intent is only partly implemented.
- `contradicts` — implementation and authoritative intent conflict.
- `unrequested` — behavior was added without supported intent.
- `owner-decision` — ambiguity is genuinely product-level.

## Escalation

Technical drift should normally be repaired autonomously.

Only `owner-decision` findings should interrupt the owner, and they must be translated into observable product consequences.
