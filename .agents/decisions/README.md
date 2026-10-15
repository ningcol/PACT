# Durable Decisions

Decision records preserve **why** a durable engineering choice exists.

Create a Decision Record only when **both** conditions hold:

1. The choice or rejected alternative has long-term maintenance value: a future
   agent is likely to need the constraint, trade-off, or reason again.
2. That rationale **cannot be recovered reliably** from code, tests, confirmed
   product rules, current architecture, or ordinary documentation.

A substantial change is not, by itself, a reason to write a Decision Record.
Do not create one merely to record that work happened.

## Five-question admission review

Before writing or retaining any Decision, answer all five questions using actual
evidence (no synthetic approval narrative):

1. What **specific future error** would be repeated without this rationale?
2. Why is the reason **not reliably derivable** from code, tests, current
   architecture, confirmed rules or normal documentation?
3. For what future duration and **under which premises** does it matter?
4. What is its **single authoritative home**, and which existing record should
   this link to rather than repeat?
5. What irreplaceable constraint would be lost **if this Decision were deleted**?

A “no” or unknown answer normally keeps the information in the Task/Change,
ordinary tests or architecture doc instead. A genuine long-term non-derivable
security decision may qualify despite a small patch. Do not force a Decision
merely because a test failed or the patch was substantial.

## Rejected alternatives

A **rejected** Decision can be more valuable than a rejected pull request:
keep the alternative, why it was considered, evidence for the rejection,
scope/premises and explicit **revisit conditions**. Mark untested ideas and
owner-confirmed conclusions separately in prose, never invent experimental
results. Retrieving the rejected rationale is **not** a permanent prohibition;
compare its original premises against today's task before reusing it.

## Supersession and reference safety

- **Full supersession:** the new active Decision carries forward every still
  relevant reason, invariant and risk; the old one points to the new Decision
  and becomes historical. Update inbound links to the new current authority
  when relevant, without breaking historical audit links.
- **Partial supersession:** enumerate which older constraints remain in force,
  keep a discoverable route to them, and supersede only the obsolete scope.
  Never silently delete the old constraints because a newer file exists.
- After a move/rename, inspect both metadata (`related`, `supersedes`) and
  Markdown links; run `pact check` and impacted regression tests. ID, path and
  relative target must resolve. Status labels cannot prove semantic validity.
- A completed Change or resolved Drift may be proposed for *manual* cleanup
  after checking Product Truth ownership, backlinks, and retention obligations;
  nothing is automatically deleted or archived based on file age.

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

`pact audit --json` lists explicitly superseded decisions as
`decision_retention_candidates` for review, not automatic archival. For the
optional review procedure, see [Knowledge Gardening](../skills/knowledge-gardening.md).

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
