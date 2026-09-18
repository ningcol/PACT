# Human Interface Contract

The owner should be able to control the product without becoming the technical reviewer.

## Default owner role

Product/project owner, not code reviewer.

## Owner-facing language

Prefer:

- user behavior;
- business behavior;
- page/flow changes;
- data meaning;
- observable consequences;
- verified scenarios;
- unresolved product risks.

Hide by default:

- class/function implementation details;
- framework internals;
- design-pattern debates;
- low-level state mechanics;
- file lists unless useful.

Technical details remain available through progressive disclosure.

## Decision translation

Bad:

> Should this use soft delete or hard delete?

Good:

> After a user deletes this record, should it be permanently unrecoverable, or should administrators be able to restore it later?

Bad:

> Should selected province live in URL state or global state?

Good:

> After a page refresh, should the user stay on the province they selected, or return to the default province?

## Completion report semantics

A normal owner report should communicate:

- what changed;
- what changed for the user/business;
- what was actually verified;
- whether project consistency is healthy;
- whether an owner decision remains.

## Progressive disclosure

Level 1: business result and verification.

Level 2: concise cause/architecture explanation.

Level 3: technical files, symbols, diffs, implementation details.

## Vocabulary

Use canonical business terminology from `docs/product/glossary/` in owner-facing communication. Do not invent project jargon when an established term exists.
