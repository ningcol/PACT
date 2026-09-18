# PACT

**Project AI Control Plane**

PACT is a project-level control plane for AI-first software development. It helps AI agents understand project truth, discover relevant context, make technical decisions autonomously, verify outcomes, detect drift, and communicate results in owner-readable language.

## Why PACT

As projects grow, AI coding workflows tend to fail in predictable ways:

- agents understand only a local slice of the codebase;
- project terminology drifts across product, code, docs, and agents;
- technical choices are escalated to owners who should only decide product meaning;
- code, tests, architecture docs, and product rules drift apart;
- "done" is reported without durable evidence;
- future agents repeatedly rediscover why a system works the way it does.

PACT treats these as **project infrastructure problems**, not prompt-writing problems.

## Core model

```text
Owner Intent
    ↓
Human Interface
    ↓
Project Discovery
    ↓
Context Resolution
    ↓
AI Execution
    ↓
Verification
    ↓
Convergence
    ↓
Evidence
    ↓
Owner-readable Result
```

## Design principles

1. Repository is durable memory; chat is temporary.
2. One fact, one owner; reference instead of copy.
3. Separate what **should be true** from what **is currently true**.
4. Seek sufficient context, not exhaustive context.
5. AI owns implementation; humans own product meaning.
6. Increase rigor with risk and uncertainty.
7. Evidence comes before claims such as "done" or "fixed".
8. Reconcile conflicts by authority; never blindly make docs follow code.
9. Humans see product consequences by default, not implementation noise.

## Repository structure

- `AGENTS.md` — compact bootstrap and knowledge router.
- `docs/governance/` — stable PACT policies and authority boundaries.
- `docs/product/` — normative product truth, vocabulary, domains, and durable rules.
- `docs/architecture/` — current architecture, not historical rationale.
- `.agents/decisions/` — durable engineering decisions and rationale.
- `docs/changes/` — active and completed change intent.
- `docs/drift/` — known unresolved drift accepted during brownfield adoption.
- `.agents/skills/` — replaceable procedures for recurring work.
- `.pact/` — PACT configuration and derived local cache.
- `scripts/pact/` — deterministic checks and future CLI entry points.

## Status

PACT is currently in **v1 foundation design and implementation**. The first milestone focuses on:

- brownfield project initialization;
- truth ownership and canonical vocabulary;
- owner/AI decision boundaries;
- project discovery;
- convergence and drift detection;
- evidence-backed completion;
- owner-readable communication.

See `docs/design/system-overview.md` for the complete architecture and `docs/initialization.md` for adoption into an existing project.
