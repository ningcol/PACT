# Context Resolver

The Context Resolver answers:

> For this task, what project knowledge is probably relevant, and what still needs semantic judgment?

It does **not** answer:

> Have we read everything?

## 1. Input

A task should provide:

- task statement;
- goal;
- observable success;
- risk level;
- discovery query.

## 2. Output

PACT may generate a Task Context Envelope conforming to:

`.pact/schema/context-envelope.schema.json`

The deterministic resolver can populate:

- ranked artifacts from Project Discovery;
- canonical domains;
- discovered Product Rules;
- discovered Decision Records;
- durable verification targets explicitly referenced by those artifacts.

It may also identify deterministic gaps such as:

- no matching Product Rule found;
- no matching artifact found.

## 3. Candidate versus sufficient

The deterministic resolver always produces:

`status: candidate`

because lexical/index retrieval cannot prove semantic sufficiency.

An Agent may promote the envelope to:

`status: sufficient`

only after judging that it understands:

- affected behavior;
- relevant dependencies;
- applicable authority;
- verification targets;
- important unknowns.

## 4. Risk adaptation

PACT 0.3 applies a core risk policy instead of treating risk as a label.

Default behavior:

- **low** — smaller knowledge budget; code-aware discovery is off unless explicitly requested;
- **medium** — larger knowledge budget; code-aware discovery is on; completion requires machine-backed Evidence, Convergence, and Owner Report;
- **high** — largest default context budget; code-aware discovery is on; missing Architecture/Decision/contract/history context is surfaced explicitly; completion requires machine-backed Evidence, no unresolved Evidence limitations, and fully aligned Convergence.

The Agent may increase rigor beyond the minimum. It may not use project configuration to weaken these core guarantees.

Inspect the current policy with:

```bash
python3 pact.py risk high --json
```

## 5. Stop condition

Stop retrieving when additional context is unlikely to materially change:

- impact understanding;
- authority interpretation;
- implementation constraints;
- verification plan.

This prevents context collection from becoming a ritual or token sink.
