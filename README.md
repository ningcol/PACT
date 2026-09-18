# PACT

**Project AI Control Plane**

PACT is a project-level control plane for AI-first software development.

It helps AI agents understand project truth, discover relevant context, make technical decisions autonomously, verify outcomes, detect drift, and communicate results in owner-readable language.

PACT is **not** a prompt bundle, a Skill, or a multi-agent framework. It is the durable project layer that any single-agent or multi-agent execution strategy can consume.

## Why PACT

As projects grow, AI coding workflows tend to fail in predictable ways:

- agents understand only a local slice of the codebase;
- project terminology drifts across product, code, docs, and agents;
- technical choices are escalated to owners who should only decide product meaning;
- code, tests, architecture docs, and product rules drift apart;
- "done" is reported without durable evidence;
- future agents repeatedly rediscover why a system works the way it does.

PACT treats these as **project infrastructure problems**, not prompt-writing problems.

## Core loop

```text
Owner Intent
    ↓
Project Discovery
    ↓
Context Resolution
    ↓
AI Execution
    ↓
Verification / Evidence
    ↓
Convergence
    ↓
Owner-readable Result
```

## Core principles

1. Repository is durable memory; chat is temporary.
2. One fact, one owner; reference instead of copy.
3. Separate what **should be true** from what **is currently true**.
4. Seek sufficient context, not exhaustive context.
5. AI owns implementation; humans own product meaning.
6. Increase rigor with risk and uncertainty.
7. Evidence comes before claims such as "done" or "fixed".
8. Reconcile conflicts by authority; never blindly make docs follow code.
9. Humans see product consequences by default, not implementation noise.

## Quick start

Install the small Python runtime dependencies:

```bash
python -m pip install -r scripts/pact/requirements.txt
```

Inspect this repository:

```bash
python scripts/pact/pact.py doctor
python scripts/pact/pact.py audit
```

Discover project knowledge:

```bash
python scripts/pact/pact.py discover "product truth"
```

Build a candidate task context:

```bash
python scripts/pact/pact.py context "fix province switching" \
  --success "Displayed data follows the selected province" \
  --risk medium
```

Analyze changed-file impact:

```bash
python scripts/pact/pact.py impact --base main --json
```

## Adopt PACT in an existing project

From a PACT checkout:

```bash
# Preview only — writes nothing.
python scripts/pact/pact.py init --target ../my-existing-project

# Create only missing scaffold files.
python scripts/pact/pact.py init --target ../my-existing-project --apply
```

Safety rules:

- dry-run is the default;
- existing files are never overwritten;
- an existing `AGENTS.md` is preserved;
- PACT does not infer confirmed Product Truth from code;
- historical documentation does not need to be fully backfilled before adoption.

After adoption:

```bash
cd ../my-existing-project
python -m pip install -r scripts/pact/requirements.txt
python scripts/pact/pact.py doctor --strict
python scripts/pact/pact.py audit
```

See `docs/initialization.md` and `docs/initialization-checklist.md`.

## Runtime commands

```text
init       safely scaffold PACT into an existing repository
check      deterministic artifact checks
doctor     repository readiness
audit      repository health inventory
map        rebuild disposable discovery index
discover   locate project knowledge
context    build candidate Task Context Envelope
impact     map changed files to project knowledge
converge   validate semantic Convergence Reports
evidence   validate Evidence Receipts
report     render evidence-backed Owner Reports
```

## Repository structure

- `AGENTS.md` — compact bootstrap and knowledge router.
- `docs/governance/` — stable authority and collaboration rules.
- `docs/product/` — normative Product Truth and canonical vocabulary.
- `docs/architecture/` — current architecture.
- `.agents/decisions/` — durable engineering rationale.
- `docs/changes/` — current and historical change intent.
- `docs/drift/` — known/resolved/accepted drift artifacts.
- `.agents/skills/` — replaceable procedures.
- `.pact/schema/` — machine-readable contracts.
- `.pact/cache/` — disposable derived indexes.
- `scripts/pact/` — runtime tools.

## Deterministic vs semantic

PACT deliberately separates two kinds of control.

**Deterministic tooling may FAIL** when the machine can establish a fact: malformed metadata, duplicate IDs, invalid lifecycle, broken executable constraints, failed tests.

**Semantic review should WARN/reconcile** when meaning requires judgment: stale architecture, missing durable decision, Product Truth conflict, unrequested behavior.

The rule is:

> **If a machine can establish the fact, FAIL. If it can only infer, review.**

## Status

PACT v1 currently includes the executable foundation for:

- brownfield initialization;
- Truth ownership and artifact lifecycle;
- Project Discovery;
- candidate Context Resolution;
- conservative Impact Analysis;
- Convergence Reports;
- Evidence Receipts;
- evidence-backed Owner Reports;
- deterministic checks, Doctor, and Audit.

The next iterations can improve semantic retrieval, code/AST relationships, project-specific fitness functions, and integrations without changing the core control-plane contracts.
