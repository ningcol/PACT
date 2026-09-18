# PACT System Overview

## 1. Positioning

PACT is a **Project AI Control Plane**. It is not a skill, prompt bundle, or multi-agent framework.

It defines the durable project interfaces that any current or future agent should consume:

- truth and authority;
- discovery and context;
- decision ownership;
- verification and evidence;
- convergence and drift handling;
- owner-facing communication.

Execution strategies remain replaceable: a single Codex session, Claude Code, multiple agents, MCP tools, or future autonomous systems can all sit beneath PACT.

## 2. Control loop

```text
Product Intent
    ↓
Project Truth
    ↓
Discovery + Context Resolution
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
    ↓
New confirmed product decision (when needed)
    └────────────→ Project Truth
```

## 3. Core subsystems

### Governance

Defines constitution, truth ownership, decision authority, completion, and the human interface.

### Truth Plane

Separates:

- normative product truth — what should happen;
- descriptive truth — what currently happens;
- current architecture — how the system is structured now;
- decision rationale — why durable engineering choices exist;
- change intent — what a current task intends to change;
- generated truth — facts mechanically derived from code/schema;
- evidence — what was actually verified.

### Project Discovery

Lets a human or agent locate a feature even when they remember only the business concept, page, symptom, or historical reason.

Discovery should resolve natural language → canonical vocabulary/domain → rules/decisions/architecture/code/tests/history.

### Context Resolver

Builds a task-specific context envelope and stops when context is sufficient for a reliable decision.

It must be risk-adaptive rather than forcing every task through the same workflow.

### Decision Authority

Technical implementation choices are autonomous by default. Owner attention is reserved for product meaning, irreversible outcomes, permissions/policy, or material risk/cost.

### Verification

Verification profiles describe outcomes that require evidence. Skills and tools decide the concrete procedure.

### Convergence

Compares desired state with actual state across product rules, specs, architecture, tests, docs, design, and runtime behavior.

### Human Interface

Translates engineering state into owner-readable consequences without degrading the technical language available internally to agents.

## 4. Stable versus replaceable layers

Stable:

- truth ownership;
- authority boundaries;
- product meaning;
- evidence requirements;
- human-facing semantics.

Replaceable:

- exact agent workflow;
- search implementation;
- model/provider;
- tools/MCP;
- skills;
- CLI internals;
- index/cache format.

This separation prevents today's model limitations from becoming tomorrow's permanent process constraints.

## 5. Brownfield first

PACT is designed primarily for existing projects.

Adoption should be forward-only:

- establish current architecture;
- establish canonical vocabulary;
- confirm a small product-truth baseline;
- record only durable decisions still relevant today;
- register known drift rather than trying to clean the entire history;
- begin governance from the adoption point forward.

See `docs/initialization.md`.
