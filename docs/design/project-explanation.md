# Project Explanation

Project Explanation serves the owner question:

> I remember this feature or business behavior, but I no longer remember where it lives, how it works, or why it was designed this way.

## 1. Two-stage design

PACT deliberately separates:

```text
deterministic evidence preparation
            ↓
semantic owner-readable explanation
```

`pact explain` produces an Explanation Packet.

It does **not** claim to know the final semantic answer by itself.

An Agent then uses the packet, and when necessary code/runtime/Git evidence, to explain the project in Owner Language.

## 2. Evidence groups

The packet separates:

- Product Truth — what should be true;
- Architecture — current structural descriptions;
- Decisions — durable evidence for why;
- Changes — current/historical change intent;
- Drift — known inconsistencies;
- Other — supporting project material.

This prevents a design rationale from being inferred from current code or architecture prose.

## 3. Important gaps

The packet explicitly reports missing evidence.

Examples:

- no confirmed Product Truth found;
- no durable Decision Record found;
- no current Architecture artifact found;
- known Drift exists.

If no Decision evidence exists, the final explanation must not invent a reason.

It may instead say:

> I can see how it works, but the repository does not currently preserve a durable record of why this choice was made.

## 4. Current behavior

Repository documentation alone may not establish current runtime behavior.

When an owner asks "how does it work today?", the Agent should inspect actual code, tests, and runtime behavior when material.

## 5. Recent changes

If change artifacts are insufficient, inspect Git history.

Do not describe something as "recent" solely because its document ranked highly in lexical search.

## 6. Owner output

A good explanation usually answers:

1. What is this?
2. What should it do?
3. How does it work today?
4. Why was it designed this way, if rationale is actually recorded?
5. Which product areas depend on it?
6. What changed materially?
7. What drift or uncertainty remains?

Technical files and symbols are progressive disclosure, not the default explanation.
