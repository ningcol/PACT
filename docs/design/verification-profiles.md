# Verification Profiles

PACT does not force every task through the same test procedure. It defines outcome-oriented verification profiles that agents adapt to project reality.

## Principle

Verification answers:

> What observable claim must be true before this task can be called complete?

The concrete tools may change over time.

## Frontend behavior

Typical claims:

- build succeeds;
- target interaction works in a browser;
- relevant loading/empty/error states behave correctly;
- important cross-state transitions remain correct;
- visible regression risk is checked.

## Backend/API behavior

Typical claims:

- relevant tests pass;
- request/response behavior matches the contract;
- error behavior is verified;
- authorization rules are preserved;
- important downstream callers remain compatible.

## Schema/data change

Typical claims:

- migration succeeds;
- existing data remains valid;
- backward compatibility is understood;
- rollback/recovery expectations are tested when required;
- contracts generated from schema are aligned.

## Permission/security change

Typical claims:

- allowed roles can perform the action;
- disallowed roles cannot;
- server-side enforcement exists where required;
- client-visible state does not masquerade as authorization truth.

## Visual change

Typical claims:

- target screen matches accepted design intent;
- correct design assets/tokens are used;
- relevant viewport/state combinations are checked.

## Refactor

Typical claims:

- externally observable behavior is unchanged;
- existing tests remain green;
- affected architecture invariants still hold.

## Risk adaptation

Low-risk work may need only targeted evidence.

High-risk work should produce stronger and more durable evidence.

PACT profiles define expected outcomes; Skills define today's concrete procedure.
