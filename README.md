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

PACT core uses only the Python 3.11+ standard library. No pip install or virtualenv is required.

### Recommended Agent surface

Start with the small task-oriented surface:

```bash
# Is the project/Pact baseline healthy?
python3 pact.py status

# I remember the feature/business behavior, but not where or why it exists.
python3 pact.py inspect "password reset" \
  --query "credential recovery reset token" \
  --query "resetPassword auth service"

# Prepare risk-adaptive context for implementation.
python3 pact.py task prepare "fix province switching" \
  --success "Displayed data follows the selected province" \
  --risk medium \
  --query "province switching displayed data" \
  --query "selectedProvince region context"

# After the Agent has created Evidence + Convergence + Owner Report:
python3 pact.py task finish <TASK-ID>
```

`task prepare` also writes a machine-readable Task Contract. The required `--success` becomes the first acceptance criterion; use repeatable `--accept` for additional observable criteria and repeatable `--constraint` for conditions that must remain true. Evidence claims that prove acceptance list the relevant `AC-*` IDs. `task finish` rejects completion when any criterion lacks passing Evidence or when verified acceptance is omitted from the Owner Report.

These commands compose the lower-level PACT primitives; they do not replace them. Stronger agents may use `discover`, `context`, `impact`, `run`, `evidence`, `converge`, `report`, and `complete` directly when that is more efficient.

`task prepare` does **not** invent Product Truth or completion evidence. `task finish` validates an existing completion bundle rather than generating semantic claims for the Agent. In Git projects it also derives the files whose final content changed since preparation, writes a final Impact report, and requires Convergence `change_coverage` rationale for every task-changed path.

Task Context is bounded by both hard artifact-count limits and a soft risk-adaptive estimated materialization-token budget. The estimate is derived from repository file size, not from reading file bodies into PACT. Use `--token-budget` only when an Agent has a concrete reason to override the default risk budget.

## Adopt PACT in an existing project

You do **not** need to clone PACT or install Python packages.

Recommended bootstrap flow:

```bash
# Pin a tag or exact commit for reproducibility.
PACT_REF="<tag-or-commit>"

curl -fsSL \
  "https://raw.githubusercontent.com/ningcol/PACT/$PACT_REF/bootstrap.py" \
  -o /tmp/pact-bootstrap.py

# Preview only — writes nothing.
python3 /tmp/pact-bootstrap.py init \
  --target ../my-existing-project \
  --ref "$PACT_REF"

# Apply after reviewing the plan.
python3 /tmp/pact-bootstrap.py init \
  --target ../my-existing-project \
  --ref "$PACT_REF" \
  --apply

# Optional separate PACT CI workflow.
python3 /tmp/pact-bootstrap.py init \
  --target ../my-existing-project \
  --ref "$PACT_REF" \
  --apply \
  --github-actions
```

For a quick moving-main trial, use `--ref main`; PACT prints a warning that this is not reproducible.

Later, upgrade without cloning:

```bash
PACT_REF="<new-tag-or-commit>"
curl -fsSL \
  "https://raw.githubusercontent.com/ningcol/PACT/$PACT_REF/bootstrap.py" \
  -o /tmp/pact-bootstrap.py

# Preview upgrade.
python3 /tmp/pact-bootstrap.py upgrade \
  --target ../my-existing-project \
  --ref "$PACT_REF"

# Transactional apply.
python3 /tmp/pact-bootstrap.py upgrade \
  --target ../my-existing-project \
  --ref "$PACT_REF" \
  --apply
```

A local PACT checkout remains supported for development/offline use.

Safety rules:

- dry-run is the default;
- existing files are never overwritten;
- an existing `AGENTS.md` is preserved;
- fresh adoption uses one compact install surface instead of copying empty knowledge/lifecycle scaffold;
- Product/Architecture/Decision/Change/Drift/Skill locations are created only when real durable project knowledge needs them;
- PACT does not infer confirmed Product Truth from code;
- historical documentation does not need to be fully backfilled before adoption.

After adoption:

```bash
cd ../my-existing-project
python3 pact.py doctor --strict
python pact.py readiness
python pact.py audit
```

See `docs/initialization.md` and `docs/initialization-checklist.md`.

## Runtime commands

Recommended:

```text
status             project foundation/readiness/health summary
inspect            inspect a remembered feature/business behavior
task prepare       prepare risk-adaptive task context
task finish        validate an existing completion bundle
task status        show one prepared task
```

Setup / maintenance:

```text
init       safely scaffold PACT into an existing repository
upgrade    safely update unchanged framework-managed files
version    show runtime/install version information
check      deterministic artifact checks
doctor     PACT foundation health
readiness  explicit baseline readiness
audit      repository health inventory
owner      validate/expose project Owner Profile
risk       show core low/medium/high rigor policy
fitness    run project-owned architecture invariants
map        rebuild disposable discovery index
code-map   rebuild generated local import/symbol relationships
discover   locate project knowledge
explain    prepare evidence for an owner-readable project explanation
context    build candidate Task Context Envelope
impact     map changed files to project knowledge
run        execute a verification command and write a run receipt
converge   validate semantic Convergence Reports
evidence   validate source-backed Evidence Receipts
report     render evidence-backed Owner Reports
complete   validate Evidence + Convergence + Owner Report as one gate
eval       validate/summarize pilot records or derive machine task observations
```

The long list above is the advanced primitive layer, not the expected everyday interface.

For local evidence-driven evaluation, `python pact.py eval --task <TASK-ID> --json` derives one machine observation and `python pact.py eval --all-tasks --json` summarizes all local prepared tasks. Human interaction/comprehension/overhead metrics remain explicitly outside machine inference.

## Discovery, Explain, and Context

These are intentionally separate:

- **Discover** answers: "Where is the relevant project knowledge?"
- **Explain** answers: "What evidence do we need to explain this feature/business behavior correctly?"
- **Context** answers: "What does this implementation task need to understand before changing behavior?"

`explain` does not invent a final narrative. If no Decision Record exists, it explicitly reports that the durable reason is missing instead of fabricating one.

`inspect` accepts repeatable `--query` values for business/canonical/code search hypotheses. The positional query remains the owner's remembered behavior; extra queries improve retrieval only and never become Product Truth. Use `--code-limit` when the default code candidate budget should be smaller than the knowledge limit.

## Framework updates do not overwrite project truth

PACT records installation provenance in `.pact/install.json`.

Framework runtime/template files can be upgraded only if they have not been locally modified since the previous install. Runtime protocol schemas are embedded in the compact `pact.pyz` instead of copied into adopted projects. Project-owned seeds such as Owner config, baseline state, governance, Agent Skills, and AGENTS are never silently overwritten.

If both a framework-managed target file and the newer PACT source changed, automatic upgrade stops before changing anything.

Upgrade apply is transactional: replacement files are staged first, current files and the install manifest are backed up, replacements/removals are rollback-aware, and any apply/validation failure triggers rollback. Obsolete framework-managed files are removed automatically only when unchanged since the prior install; locally modified obsolete files are preserved.

## Minimal installation is not PACT-ready

`pact init` intentionally creates only the control-plane nucleus plus `.pact/baseline.toml` with review areas marked `pending`. Empty knowledge folders/templates are not materialized just to make PACT look complete.

PACT derives adoption state as:

```text
scaffolded
→ foundation-valid
→ baseline-in-progress
→ pact-ready
```

This prevents generated folders/templates from being mistaken for a reviewed Product/Architecture baseline.

Only mark vocabulary, Product Truth, architecture, authority, Owner Profile, verification reality, and Known Drift as reviewed (or explicitly not applicable) after they were actually inspected.

Pending global baseline review is **advisory** in normal `pact status`. A fresh project can be operationally healthy while its repository-wide baseline is still incomplete. Use `pact readiness --require-ready` only when the project intentionally chooses full baseline review as a governance gate. Task safety remains enforced through Task Contract, Context, Evidence, Convergence, and completion policy.

## Repository structure

Fresh adopted projects start with the control-plane nucleus only:

- `AGENTS.md` — compact bootstrap and knowledge router (or existing project guide, with merge guidance under `.pact/`).
- `pact.py` — stable repository-root entry point.
- `.pact/pact.pyz` — compact installed PACT runtime.
- `.pact/config.toml` — Owner Profile.
- `.pact/baseline.toml` — explicit adoption review state.
- `.pact/fitness.toml` — project-owned executable architecture checks.
- `.pact/install.json` — install ownership/provenance.
- runtime protocol schemas — embedded inside `.pact/pact.pyz`.

These durable knowledge locations are **lazy**: they may be absent until the project has real knowledge to preserve.

- `docs/governance/` — project-specific authority/collaboration extensions.
- `docs/product/` — normative Product Truth and canonical vocabulary.
- `docs/architecture/` — current architecture.
- `.agents/decisions/` — durable engineering rationale.
- `docs/changes/` — current and historical change intent.
- `docs/drift/` — known/resolved/accepted drift artifacts.
- `.agents/skills/` — replaceable procedures.

`.pact/cache/`, `.pact/tasks/`, `.pact/runs/`, `.pact/completions/`, and `.pact/tmp/` are local generated control-plane state and are ignored by the nested `.pact/.gitignore`. They support execution/evaluation but are not durable project truth. `scripts/pact/` is the source-checkout runtime used when developing PACT itself and is not copied into new installs.

## Deterministic vs semantic

PACT deliberately separates two kinds of control.

**Deterministic tooling may FAIL** when the machine can establish a fact: malformed metadata, duplicate IDs, invalid lifecycle, broken executable constraints, failed tests.

**Semantic review should WARN/reconcile** when meaning requires judgment: stale architecture, missing durable decision, Product Truth conflict, unrequested behavior.

The rule is:

> **If a machine can establish the fact, FAIL. If it can only infer, review.**

## Status

**Main runtime:** 0.4.0-dev.1 (pre-release)  
**Last release baseline:** 0.3.0  
**Control-plane protocol:** v1

Current `main` is the development line for the next minor release. It includes the 0.3 foundation plus:

- compact single-file `.pact/pact.pyz` runtime with embedded protocol schemas;
- minimal/lazy brownfield adoption (8 managed files in the real pilot);
- stricter Evidence provenance and workspace-bound verification;
- advisory daily readiness with explicit full-baseline gating;
- atomic task preparation and local generated task/run/completion state;
- deterministic multi-query retrieval with equal final code budgets;
- risk-adaptive estimated materialization-token budgets;
- multi-query remembered-feature `inspect`;
- actual task changed-file attribution, final Impact, and Convergence change coverage;
- generic lexical code retrieval for common unsupported structured languages without fabricated edges;
- full correctness CI separated from the 3×3 portability matrix.

This development version is **not** a GitHub Release or immutable release tag. For reproducible external adoption, prefer an exact commit until a formal release is cut.

The remaining high-level validation work is ongoing evaluation with observed real tasks, plus the explicit owner decision on repository licensing.

## Project governance

- Security reporting: `SECURITY.md`
- Contributing: `CONTRIBUTING.md`
- Release process: `docs/releasing.md`
- Repository license: pending explicit owner decision; public visibility alone is not treated as a license grant.
