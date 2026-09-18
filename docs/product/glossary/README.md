# Domain Vocabulary

Canonical vocabulary helps humans and agents find the same concept even when old code and documents use different names.

## Template

```yaml
id: DOMAIN-EXAMPLE
canonical_name: Example Name

meaning:
  Precise business meaning.

owner_terms:
  - Example Name

code_aliases:
  - exampleName
  - legacy_example

historical_aliases:
  - Old Name

not_the_same_as:
  - Similar but different concept
```

## Rules

- Do not force immediate code-wide renaming during PACT adoption.
- Map aliases first; converge naming over time.
- Canonical terms are preferred in owner-facing communication and product truth.
- Distinguish same-name/different-meaning concepts explicitly.
