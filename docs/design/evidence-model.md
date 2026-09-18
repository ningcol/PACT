# Evidence Model

PACT treats completion claims as evidence-backed statements.

The Evidence layer answers:

> What was actually checked, what passed, what failed, and what could not be verified?

## 1. Evidence is not agent opinion

Invalid:

```text
Agent: "I verified the feature."
Evidence: "The agent says it verified the feature."
```

Valid evidence references an observable result, such as:

- a test command and result;
- browser/E2E scenario;
- screenshot or visual comparison;
- runtime trace/log;
- schema/contract check;
- deterministic architecture check;
- manual owner-confirmed observation when explicitly recorded.

## 2. Receipt model

A task may emit an Evidence Receipt conforming to:

`.pact/schema/evidence-receipt.schema.json`

The receipt records:

- task and risk level;
- required outcome claims;
- whether each claim passed, failed, or remains unverified;
- concrete evidence references;
- limitations.

## 3. Required versus optional claims

A completion-critical outcome uses `required: true`.

If any required claim is:

- `fail`; or
- `unverified`;

the task cannot be represented as fully completed.

Optional checks may remain unverified when risk is acceptable and the limitation is visible.

## 4. Retention

Evidence retention follows risk:

- low risk: session/PR evidence may be enough;
- medium risk: keep a concise PR/change receipt;
- high risk: prefer durable CI/runtime artifacts.

PACT does not require every receipt to be committed permanently.

## 5. Human Interface relationship

The Owner Report may cite only evidence IDs present in the receipt.

This prevents an owner-facing summary from claiming stronger verification than the underlying evidence supports.
