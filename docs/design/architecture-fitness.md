# Architecture Fitness Functions

PACT distinguishes architecture prose from architecture invariants that can be checked mechanically.

A **fitness function** is a project-owned executable constraint such as:

- forbidden dependency direction;
- package cycle policy;
- public/private module boundary;
- persistence access boundary;
- generated contract consistency;
- required layering invariant.

## PACT's role

PACT defines:

- how checks are registered;
- how they are executed safely;
- how error vs warning results are reported.

PACT does **not** define which architecture patterns a project must use.

There is no built-in requirement for DDD, Clean Architecture, repositories, events, or any other pattern.

## Configuration

Project checks live in:

`.pact/fitness.yaml`

Example:

```yaml
version: 1

checks:
  - id: no-domain-to-ui
    description: Domain code must not import UI modules.
    command:
      - python
      - scripts/architecture/check_domain_dependencies.py
    severity: error
    timeout_seconds: 120
```

Commands are argument arrays and execute without a shell.

## Severity

### error

A non-zero exit code is a deterministic violation and makes `pact fitness` fail.

Use this only when the project can reliably establish the invariant.

### warn

A non-zero exit code is surfaced but does not fail the command.

Use warnings during migrations or for constraints that are intentionally informative.

## Ownership

`.pact/fitness.yaml` is a project seed and becomes project-owned after initialization.

PACT upgrades never silently replace it.

The scripts/checkers referenced by the configuration are also project-owned.

## Relationship to semantic review

Fitness functions answer machine-checkable facts.

Questions such as:

- "is this abstraction still a good idea?";
- "should we split this domain?";
- "does this architecture document still describe the right product model?"

remain semantic review / Decision concerns.
