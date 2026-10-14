# Durable Decisions

Decision records preserve **why** a durable engineering choice exists.

Create a Decision Record only when **both** conditions hold:

1. The choice or rejected alternative has long-term maintenance value: a future
   agent is likely to need the constraint, trade-off, or reason again.
2. That rationale **cannot be recovered reliably** from code, tests, confirmed
   product rules, current architecture, or ordinary documentation.

A substantial change is not, by itself, a reason to write a Decision Record.
Do not create one merely to record that work happened.

## Threshold

Candidates worth considering, **only when both conditions above hold**:

- a non-obvious architecture boundary or cross-module contract;
- persistence/schema ownership and data migration trade-offs;
- security or concurrency invariants not obvious from the implementation;
- a durable infrastructure, deployment, or testing trade-off;
- a rejected alternative future agents are likely to propose again.

Prefer an executable check for mechanically verifiable invariants, an architecture
doc for how the system currently works, and a Change/Task artifact for plans and
progress. Link to an existing authoritative record rather than copying it.

Do not create decisions for formatting, ordinary UI adjustments, simple CRUD,
small bug fixes, routine refactors, or uncontroversial implementation details.
A small but non-obvious security or data-integrity decision may still qualify.

## Retention

Implemented decisions are **not automatically permanent active instructions**.
During relevant maintenance, review whether their rationale is still needed:

- Keep `implemented` while the trade-off constrains current engineering.
- Use `superseded` with a reference to the new decision when the rationale changes;
  preserve the earlier choice as history.
- Move a no-longer-active record to `archived/` with `status = "archived"`
  when it remains useful only as historical context.

Archiving is a reviewed semantic choice, not a heuristic based solely on age or
lack of backlinks. Do not delete historical rationale or silently rewrite it to
match current code.

## Lifecycle

```text
proposed
  ├──→ rejected
  ↓
implemented
  ├──→ superseded
  ↓
archived
```

When core rationale changes, create a new decision that supersedes the old one. Do not rewrite history.

Use `TEMPLATE.md`.
