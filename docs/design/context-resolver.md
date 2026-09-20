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
- one or more discovery queries.

The owner does not need to write these queries. The Agent may expand the owner request into a small set of business/canonical/code search hypotheses and pass repeated `--query` values.

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

## 4. Multi-query and materialization budgets

Each query is retrieved independently. PACT deduplicates and fuses peer query lists, then applies the final risk-adaptive Context budgets.

When the first explicit query is the original task wording and later queries are Agent-generated search hypotheses (the recommended high-level `task prepare` pattern), PACT first resolves the task-only Context under the same count/token budgets. Files already selected for that primary task remain canonical; fused supplemental queries may fill remaining capacity but do not silently evict the task-selected Context. This is deliberately different from low-level peer multi-query retrieval, where callers may supply several equal retrieval intents.

Two independent controls are used:

- **hard artifact-count limits** cap selected knowledge/code paths;
- a **soft estimated materialization-token budget** limits the approximate downstream cost of reading those files.

PACT estimates tokens deterministically from repository file size using `UTF-8 bytes / 4`. This is a stable budget heuristic, **not** an exact tokenizer result and not a claim about any particular model's final token count.

Discovery may inspect a wider candidate pool than the final Context. Selection then prefers authority/relevance while allowing later smaller candidates to fit when an earlier large candidate would exceed the soft budget.

Confirmed Product Rules and implemented Decisions are authority evidence. They are not silently dropped only because of the soft token budget; any resulting overage is recorded explicitly. Hard artifact-count limits remain hard.

The Context Envelope records:

- `discovery_queries`;
- per-artifact `estimated_tokens`;
- `context_budget.limit_tokens`;
- selected/candidate estimated tokens;
- candidates dropped by token budget vs count limits;
- explicit authority overage.

Use `--token-budget` on `context` or `task prepare` only when the default risk budget should be overridden.

## 5. Risk adaptation

PACT applies a core risk policy instead of treating risk as a label.

Default behavior:

- **low** — smaller artifact/token budgets; code-aware discovery is off unless explicitly requested;
- **medium** — larger artifact/token budgets; code-aware discovery is on; completion requires current workspace-bound `pact-run` Evidence for required pass claims, plus Convergence and Owner Report;
- **high** — largest default artifact/token budgets; code-aware discovery is on; missing Architecture/Decision/contract/history context is surfaced explicitly; completion requires current workspace-bound `pact-run` Evidence for required pass claims, no unresolved Evidence limitations, and fully aligned Convergence.

The Agent may increase rigor beyond the minimum. It may not use project configuration to weaken these core guarantees.

Inspect the current policy with:

```bash
python3 pact.py risk high --json
```

## 6. Stop condition

Stop retrieving when additional context is unlikely to materially change:

- impact understanding;
- authority interpretation;
- implementation constraints;
- verification plan.

This prevents context collection from becoming a ritual or token sink.
