# PACT Runtime

PACT core requires Python 3.11+ and uses only the standard library. No runtime pip dependencies are required.

The stable v1 entry point is:

```bash
python scripts/pact/pact.py <command> [args...]
```

## Recommended agent surface

```text
status             project foundation/readiness/health summary
inspect            combined explanation + code evidence packet
task prepare       Task Contract + risk-adaptive context preparation
task finish        acceptance-aware completion-bundle gate
task status        one-task state
```

The commands below remain stable advanced primitives.

## Available primitives

```text
init       safely scaffold PACT into an existing repository
upgrade    safely update unchanged framework-managed PACT files
version    show source/installed PACT runtime versions
check      deterministic artifact checks
schema-lint validate that schemas use only runtime-supported keywords
workflow-lint require immutable external GitHub Action pins
doctor     deterministic PACT foundation health
readiness  explicit brownfield baseline readiness
audit      deterministic repository health inventory
owner      validate and expose project Owner Profile
risk       show core low/medium/high rigor policy
fitness    run project-owned executable architecture invariants
map        rebuild disposable project map
code-map   rebuild disposable local code relationship map
discover   deterministic project discovery
explain    build an explanation evidence packet for an owner query
context    build candidate Task Context Envelope
impact     map changed files to deterministic/candidate project impacts
converge   validate/summarize semantic Convergence Report
evidence   validate completion Evidence Receipt
report     validate and render evidence-backed Owner Report
eval       validate/summarize pilot records or derive machine task observations
```

Examples:

```bash
python3 pact.py status
python3 pact.py inspect "batch state"

python3 pact.py task prepare "fix province switch" \
  --success "Displayed data follows the selected province" \
  --risk medium

python3 pact.py task status <TASK-ID>
python3 pact.py task finish <TASK-ID>

# Advanced primitives:

python scripts/pact/pact.py init --target ../existing-project
python scripts/pact/pact.py init --target ../existing-project --apply
python scripts/pact/pact.py init --target ../existing-project --apply --github-actions

python scripts/pact/pact.py version --target ../existing-project
python scripts/pact/pact.py upgrade --target ../existing-project
python scripts/pact/pact.py upgrade --target ../existing-project --apply

python scripts/pact/pact.py doctor
python scripts/pact/pact.py readiness
python scripts/pact/pact.py audit --json
python scripts/pact/pact.py owner --json
python scripts/pact/pact.py risk high --json
python scripts/pact/pact.py fitness

python scripts/pact/pact.py discover "batch state"
python scripts/pact/pact.py discover "BatchService" --code

python scripts/pact/pact.py code-map
python scripts/pact/pact.py impact --files src/example.ts --code --json

python scripts/pact/pact.py explain "why does the workspace follow the current batch?" --json

python scripts/pact/pact.py context "fix province switch" \
  --success "Displayed data follows the selected province" \
  --risk medium

python scripts/pact/pact.py context "upgrade runtime" \
  --success "Upgrade behavior remains safe" \
  --risk medium \
  --code

python scripts/pact/pact.py impact --base main --json

python scripts/pact/pact.py eval .pact/examples/pilot-evaluation.example.json
```

## Architecture fitness

`.pact/fitness.toml` is project-owned.

PACT only standardizes how executable invariants are registered and reported; it does not prescribe architecture patterns.

`severity: error` failures block. `severity: warn` failures are reported without blocking.

## Code-aware discovery

Code relationships are generated and disposable.

`discover --code` searches code paths/symbols/import text and adds one-hop import neighbors.

`impact` and `context` follow the core risk profile by default:
- low: no code expansion unless explicitly requested;
- medium/high: code-aware expansion enabled unless explicitly disabled.

Generated relationships carry confidence:
- `direct`: direct lexical code match;
- `relative-resolved`: relative JS/TS/Vue path resolved to a repository file;
- `ast-resolved`: Python relative import resolved from AST/package position;
- `heuristic`: repository-local Python absolute-import match whose runtime import resolution may differ.

Behavioral impact remains a candidate requiring review.

Project/Code maps use source fingerprints. A cached map is reused only while its source set is fresh; otherwise it is refreshed automatically.

On Git repositories, file enumeration uses Git's tracked/visible-untracked view and respects `.gitignore` before parsing. When only part of the source set changed, per-file parse caches reuse unchanged Markdown/symbol/import results and only reparse changed/new files.

Unsupported project-specific aliases or framework magic remain unresolved rather than guessed.

## Discovery vs Explain vs Context

- `discover`: locate relevant project artifacts.
- `explain`: organize those artifacts into Product Truth / Architecture / Decision / Change / Drift evidence for an explanation.
- `context`: build a task-oriented candidate context envelope for implementation work; `--code` adds generated code candidates when useful.

`explain` prepares evidence. An Agent still performs the semantic, owner-readable explanation and must inspect code/runtime/Git when the evidence packet says that is necessary.

## Safe upgrades

`init --apply` records `.pact/install.json` with file ownership and SHA256 provenance.

For normal users, the repository-root `bootstrap.py` can fetch a pinned PACT ref and invoke init/upgrade without cloning PACT first.

- framework-managed files are auto-updatable only when unchanged since install;
- project seed files are never overwritten;
- any true framework conflict blocks the entire automatic apply;
- replacement files are staged before mutation;
- existing targets and install manifest are backed up;
- apply/validation failure rolls back replaced files and manifest;
- obsolete framework files are reported but never auto-deleted.

Run upgrade from the newer PACT source checkout:

```bash
python scripts/pact/pact.py upgrade --target ../existing-project
python scripts/pact/pact.py upgrade --target ../existing-project --apply
```

See `docs/design/distribution-upgrades.md`.

## Doctor vs Readiness

- `doctor` answers whether PACT infrastructure/configuration is valid.
- `readiness` answers whether the existing project's repository-wide baseline was explicitly reviewed.
- `status` treats pending baseline review as an advisory, not an operational failure.

A freshly adopted project can therefore have `status=pass` while readiness remains `foundation-valid`. Use `readiness --require-ready` only when the project has explicitly chosen full baseline review as a governance gate. Task-level safety comes from the prepared Task Contract/Context and completion gates.

## Pilot evaluation

PACT evaluation is optional and task-based. It tracks dimensions such as owner technical escalations, clarification rounds, false-done prevention, Project Explain recovery, context overload, and optional process overhead.

PACT intentionally does not compute a single 0–100 score.

See `docs/evaluation/pilot-scorecard.md`.

## Safety boundary

`init` is dry-run by default and never overwrites existing files. Fresh adoption installs only the compact executable/control-plane surface, while empty Product/Architecture/Decision/Change/Drift/Skill scaffold is left unmaterialized. An existing `AGENTS.md` is preserved; PACT creates merge guidance under `.pact/` instead.

## Scoped Context intent and explicit Rule requirements (S3)

The original `pact discover QUERY` and `pact context TASK --success ...`
ranking stays unchanged without extra flags. To investigate a specific need,
use `--intent work|decision|history` (available on `discover`,
`context`, and high-level `task prepare`).

- `work` gives current confirmed Rules and implemented decisions retrieval
  priority; `decision` includes rejected rationales as evidence (not normative
  Rules); `history` helps locate superseded, archived and rejected reasons.
- `context --require-rule RULE-ID` (or `task prepare --require-rule RULE-ID`)
  is **caller-supplied only**. An absent, pending, mixed-authority or
  budget-excluded Rule ID is a hard error before Context is published; no
  mandatory Rule is invented from free text.
- Context v1 remains a closed Schema. Navigation-only governance paths and
  nearby module README locations are placed in existing advisory
  `known_unknowns` strings, **not** in `artifacts` or `applicable_rules`.
  The hints do not materialize README contents, increase normal ranked
  Context candidates or imply governance documents are Product Rules.
- README discovery examines bounded ancestors of code paths already selected,
  never the whole repository; Git-ignored, escaped, symlinked and oversized
  paths are skipped. Use these strings as human navigation metadata only.
- If migrating to a future structured Context field, first validate old/new
  producers and readers for source/installed `pact.pyz`; optional new JSON
  properties alone do not preserve compatibility with old v1
  `additionalProperties: false` consumers.

### Default weak Decision search (source-bound, conservative)

In a single-query low/medium risk task, ordinary Context now materializes
implemented Decision records when a generic body match lacks stronger
source corroboration. Unreasoned Decision candidates with no task term in
their original title or exact distinctive source phrase become
up to five source-hashed `weak_decision_hints` with total/truncated counts,
not silently dropped and **not** marked as inapplicable authority.

This changes Context materialization, **not** the indexed source, Discover
ranking or Product Rule precedence. A prepared task **must** review deferred
Decision hints in Convergence; task assist cannot draft mechanically passing
Owner acceptance while any remain unchecked. If hints are truncated, finish
fails closed and the task must be reprepared with `--full-decisions`.

Always use `--full-decisions` (on `context` or `task prepare`) when original
unrestricted Decision context is necessary. High-risk, history/decision intent,
multi-query and `--scope-first` contexts already retain the original selection.
No task-text heuristic decides whether code changes behavior. This optimization
does not prove semantic inapplicability, real Agent obedience, true billed
model-token savings or independent Owner improvement. The previously explicit
`--nonfunctional` mode below remains separate and more aggressive.

### Explicit nonfunctional Context (low-risk only)

For an **already-established no-behavior-change** task (e.g. a variable
rename, formatting-only change or spelling correction), a caller can use
`pact context "..." --success "..." --risk low --intent work --nonfunctional`
or `pact task prepare "..." ... --risk low --nonfunctional`.

This opt-in mode keeps normal documents, confirmed Rules and Decisions
explicitly cited by source-scored ID/title/alias. Other lexical Decision hits
are **deferred, not deleted**: up to five source-hashed
`nonfunctional_decision_hints.candidates` plus total/truncated counters and
an explicit warning. Deferred bodies are not injected into Context, listed
as applicable Decisions or treated as completed verification. A task prepared
with this mode **must explicitly review every visible deferred Decision in
Convergence** before finish; truncated/unknown candidate sets cannot finish
and must be re-prepared using normal Context. Mechanical Owner acceptance
drafts are blocked until those Decision hints are accounted for. The tool does
**not** infer this mode from task wording.

If behavior, security, trust, policy, or an Owner decision could change,
rerun **without** `--nonfunctional` and inspect authority sources. Medium/high
risk, history/decision intent and `--scope-first` combinations fail closed.
This is a manually selected exploratory alternative, **not** a new default or
an independent blind Agent/Owner benefit result.

PACT core requires Python 3.11+ and uses only the standard library. No runtime pip dependencies are required.

The stable v1 entry point is:

```bash
python scripts/pact/pact.py <command> [args...]
```


## Task Evidence writer locking

`task draft` and `task verify` serialize writes to each completion bundle using
a nonblocking operating-system file lock at `.task-workflow.lock` inside that
bundle. **The lock pathname intentionally stays on disk** after a successful
run; only the OS-held lock is released. An abrupt process exit also releases
the OS-held lock, so an abandoned empty sentinel from earlier PACT versions
does not require manual deletion. Do not remove the pathname while writers
may be active: that can create independent lock inodes and defeat exclusivity.

An older pre-fix PACT runtime used create-exclusive/delete semantics on the
same filename; do not run the old and new runtime against one completion
bundle concurrently. This coordinates cooperative PACT writers, not malicious
filesystem mutation or unbounded external verification commands.

## Local task state

`.pact/tasks/`, `.pact/runs/`, `.pact/completions/`, `.pact/cache/`, and `.pact/tmp/` are generated local control-plane state. Fresh init creates `.pact/.gitignore` so these paths do not pollute project Git status. They remain available locally for task status/evaluation/completion but are not durable project knowledge.

`task prepare` stages contract/context/impact under `.pact/tmp/` and publishes the task directory only after preparation succeeds. `--force` invalidates old generated completion state only after the replacement preparation has succeeded.

The runtime is deliberately hybrid:

- deterministic tooling validates facts it can reliably establish;
- semantic AI review handles meaning, impact, and sufficiency;
- the CLI never promotes heuristic guesses into authority.

Semantic uncertainty should remain a warning, Context unknown, candidate impact, Explanation gap, or Convergence finding.

## Task Contract / acceptance coverage

High-level task preparation persists `.pact/tasks/<TASK-ID>/contract.json`.

- `--success` creates `AC-1`;
- repeatable `--accept` adds `AC-2`, `AC-3`, ...;
- repeatable `--constraint` adds acceptance-bound criteria with `kind=constraint`;
- Evidence claims bind to acceptance criteria through optional `criteria: ["AC-1"]`;
- prepared tasks expose `contract_sha256`; Evidence for a Task Contract records it as `task_contract_sha256`;
- `task finish` automatically supplies the contract to the completion gate.

When a Task Contract is supplied, completion requires every acceptance criterion to have passing Evidence and requires that passing Evidence to be surfaced in Owner Report verification.


## Machine-observed task evaluation

After a task has been prepared, PACT can derive the task facts it already owns:

```bash
python scripts/pact/pact.py eval --task <TASK-ID> --json
```

The output includes acceptance coverage, Context artifact counts, run outcomes, completion-attempt blockers, Evidence state, and Convergence counts.

Human interaction fields are intentionally listed in `human_required` rather than guessed.


## Context-bound Convergence

High-level prepared tasks fingerprint the generated Task Context. Before `task finish`, the Convergence Report must bind to that exact Context and provide one coverage disposition for every `context.artifacts` entry.

This makes silent knowledge omission a completion error while keeping semantic judgment with the Agent.


## Multi-query retrieval

`discover`, `context`, and high-level `task prepare` support repeatable discovery queries.

For high-level `task prepare`, the task wording is always retained as the primary retrieval query; repeatable `--query` values add business/canonical/code hypotheses. Low-level `context` remains available when an advanced caller intentionally wants to supply the entire query set.

```bash
python pact.py context "fix province switching" \
  --success "displayed data follows the selected province" \
  --risk medium \
  --query "province switching data" \
  --query "selectedProvince region context" \
  --code
```

Each query is retrieved independently. Multi-query results are deduplicated and fused with deterministic Reciprocal Rank Fusion before the final knowledge/code budget is applied.

Single-query behavior remains compatible with the previous surface.
