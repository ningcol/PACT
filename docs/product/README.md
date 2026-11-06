# Product Truth

This area routes product knowledge. Confirmed Rules contain normative truth;
ordinary business explanations may separately describe confirmed requirements,
candidates, implementation observations and history. Location alone confirms none.

It is intentionally not a full product wiki.

## Contains

- `glossary/` — canonical business vocabulary and aliases.
- `domains/` — lightweight concept landing pages and navigation.
- `specs/` — coherent business flows, states and topic explanations in ordinary
  Markdown; no `spec` artifact type or blanket confirmed status.
- `rules/` — important constraints worth independently confirming, citing or verifying.

## Does not contain

- current implementation details;
- architecture history;
- temporary task plans;
- code-derived statements presented as confirmed truth.

Code-derived observations may be explicitly labelled in a business explanation,
with their revision and verification limits; they never become confirmed rules
solely because code implements them. Link uncertain requirements to candidate
Rules or Drift instead of marking a mixed explanation confirmed.

## Rule threshold

Create a durable product rule when it is long-lived, cross-module, easy to misunderstand, or costly to violate.

Prefer a small, trustworthy corpus over comprehensive but stale documentation.

## One authoritative body

Keep one current authoritative body for the **same fact, scope and effective
state**. Different years, roles, conditions or lifecycle states can require
different records. Keep a coherent flow and its context together. Extract only
important independently useful constraints as Rules; replace their repeated
normative prose in explanations with links. Retain conditions, exceptions,
confirmation sources and still useful historical reasons.

Domains hold meanings, aliases and navigation, never copies of full Rules,
explanations or Decision rationale. Do not create empty knowledge libraries or
Markdown mirrors of code. Architecture describes current implementation;
Decisions retain only rationale meeting their existing admission threshold;
Changes hold plan intent/deltas/acceptance; Drift holds disagreements. Receipts
and execution state remain in existing local execution directories.

## Existing projects and migration

New knowledge follows these routes. Existing authoritative locations remain
effective until an explicit, reviewed migration switches them. Ordinary READMEs,
operations manuals and established project documents outside this tree are
valid; checks do not globally require their relocation. See the bounded
[migration and maintenance procedure](../design/knowledge-maintenance.md).
