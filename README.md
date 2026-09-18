# PACT

**Project AI Control Plane**

PACT is a project-level control plane for AI-first software development.

It helps AI agents understand project truth, discover relevant context, make technical decisions autonomously, verify outcomes, detect drift, explain existing project behavior, and communicate results in owner-readable language.

PACT is **not** a prompt bundle, a Skill, or a multi-agent framework. It is the durable project layer that any single-agent or multi-agent execution strategy can consume.

## Why PACT

As projects grow, AI coding workflows tend to fail in predictable ways:

- agents understand only a local slice of the codebase;
- project terminology drifts across product, code, docs, and agents;
- technical choices are escalated to owners who should only decide product meaning;
- code, tests, architecture docs, and product rules drift apart;
- "done" is reported without durable evidence;
- future agents repeatedly rediscover why a system works the way it does;
- owners remember a feature or business rule but no longer remember where or why it was implemented.

PACT treats these as **project infrastructure problems**, not prompt-writing problems.

## Core loop

```text
Owner Intent / Question
    ↓
Project Discovery / Explanation
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
python scripts/pact/pact.py owner --json
```

Discover project knowledge:

```bash
python scripts/pact/pact.py discover "product truth"

# Opt-in code-aware expansion:
python scripts/pact/pact.py discover "BatchService" --code
```

Prepare an explanation packet when you remember the feature but not the implementation/history:

```bash
python scripts/pact/pact.py explain "why does the workspace follow the current batch?" --json
```

The packet separates Product Truth, Architecture, Decisions, Changes, and Drift. An AI agent then turns that evidence into an owner-readable explanation and expands into code/runtime/Git only when needed.

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

# Optional: also create a separate PACT GitHub Actions workflow.
python scripts/pact/pact.py init --target ../my-existing-project --apply --github-actions

# Later, from a newer PACT checkout:
python scripts/pact/pact.py upgrade --target ../my-existing-project
python scripts/pact/pact.py upgrade --target ../my-existing-project --apply
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
python scripts/pact/pact.py readiness
python scripts/pact/pact.py audit
```

See `docs/initialization.md` and `docs/initialization-checklist.md`.

## Runtime commands

```text
init       safely scaffold PACT into an existing repository
upgrade    safely update unchanged framework-managed files
version    show runtime/install version information
check      deterministic artifact checks
doctor     PACT foundation health
readiness  explicit baseline readiness
audit      repository health inventory
owner      validate/expose project Owner Profile
map        rebuild disposable discovery index
code-map   rebuild generated local import/symbol relationships
discover   locate project knowledge
explain    prepare evidence for an owner-readable project explanation
context    build candidate Task Context Envelope
impact     map changed files to project knowledge
converge   validate semantic Convergence Reports
evidence   validate Evidence Receipts
report     render evidence-backed Owner Reports
```

## Discovery, Explain, and Context

These are intentionally separate:

- **Discover** answers: "Where is the relevant project knowledge?"
- **Explain** answers: "What evidence do we need to explain this feature/business behavior correctly?"
- **Context** answers: "What does this implementation task need to understand before changing behavior?"

`explain` does not invent a final narrative. If no Decision Record exists, it explicitly reports that the durable reason is missing instead of fabricating one.

## Framework updates do not overwrite project truth

PACT records installation provenance in `.pact/install.json`.

Framework runtime/schema/template files can be upgraded only if they have not been locally modified since the previous install. Project-owned seeds such as Owner config, baseline state, governance, Agent Skills, and AGENTS are never silently overwritten.

If both a framework-managed target file and the newer PACT source changed, automatic upgrade stops before changing anything.

## Scaffolded is not PACT-ready

`pact init` intentionally creates `.pact/baseline.yaml` with review areas marked `pending`.

PACT derives adoption state as:

```text
scaffolded
→ foundation-valid
→ baseline-in-progress
→ pact-ready
```

This prevents generated folders/templates from being mistaken for a reviewed Product/Architecture baseline.

Only mark vocabulary, Product Truth, architecture, authority, Owner Profile, verification reality, and Known Drift as reviewed (or explicitly not applicable) after they were actually inspected.

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

- brownfield initialization with explicit readiness state;
- opt-in project CI integration;
- validated project Owner Profiles for language/technical-depth communication;
- Truth ownership and artifact lifecycle;
- Project Discovery with optional generated code relationships;
- Project Explanation evidence packets;
- candidate Context Resolution;
- conservative Impact Analysis;
- Convergence Reports;
- Evidence Receipts;
- evidence-backed Owner Reports;
- deterministic checks, Doctor, and Audit.

The next iterations can improve semantic retrieval, code/AST relationships, project-specific fitness functions, and integrations without changing the core control-plane contracts.
