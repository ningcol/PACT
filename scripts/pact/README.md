# PACT Automation

This directory will contain deterministic PACT checks and future CLI entry points.

Planned interfaces:

```text
pact init
pact doctor
pact explain "<query>"
pact discover "<query>"
pact impact
pact check
pact converge
pact map
pact audit
```

## v1 automation principle

A deterministic check may fail CI only when the machine can reliably establish the fact.

Examples suitable for FAIL:

- broken internal links;
- invalid decision lifecycle/path;
- modified frozen/archive policy;
- generated artifact mismatch;
- forbidden dependency;
- failed test.

Examples suitable for WARN + semantic review:

- architecture might be stale;
- durable decision might be missing;
- product rule might be affected;
- two decisions might overlap semantically.

Do not turn probabilistic guesses into hard gates merely to make PACT appear strict.
