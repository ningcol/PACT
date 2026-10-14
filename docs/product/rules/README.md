# Product Rules

Product rules are durable normative statements.

## Suggested format

```md
# RULE-<DOMAIN>-NNN — Title

Status: confirmed

## Rule

What must be true?

## Applies to

- affected feature/domain

## Observable consequence

What would a user/business stakeholder observe if this rule is followed or broken?

## Evidence / authority

Where was this rule confirmed?

## Verification

What behavior/test can verify it?
```

## Confirmed versus candidate sections

A `status = "confirmed"` Rule Artifact is authoritative as **one whole file**.
Do not combine a confirmed first half with headings such as `## 待确认` or
`## Unconfirmed` in the same Rule. Split these into separate confirmed and
candidate files and link both from a neutral domain/navigation page. A heading
heuristic in `pact audit` warns about obvious mixed authority; it cannot
establish that every unlabelled section is confirmed. Do not promote uncertain
business meaning merely because an Agent can parse the Markdown.

## Do not create rules for

- implementation preferences;
- ordinary UI spacing;
- transient tasks;
- behavior inferred only from code;
- facts already owned by generated contracts/schema.
