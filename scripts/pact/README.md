# PACT Runtime

PACT core requires Python 3.11+ and uses only the standard library. No runtime pip dependencies are required.

The stable v1 entry point is:

```bash
python scripts/pact/pact.py <command> [args...]
```

## Available commands

```text
init       safely scaffold PACT into an existing repository
upgrade    safely update unchanged framework-managed PACT files
version    show source/installed PACT runtime versions
check      deterministic artifact checks
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
eval       validate/summarize optional real-task pilot records
```

Examples:

```bash
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

Project/Code maps use source fingerprints. A cached map is reused only while its source set is fresh; otherwise it is rebuilt automatically.

Unsupported project-specific aliases or framework magic remain unresolved rather than guessed.

## Discovery vs Explain vs Context

- `discover`: locate relevant project artifacts.
- `explain`: organize those artifacts into Product Truth / Architecture / Decision / Change / Drift evidence for an explanation.
- `context`: build a task-oriented candidate context envelope for implementation work; `--code` adds generated code candidates when useful.

`explain` prepares evidence. An Agent still performs the semantic, owner-readable explanation and must inspect code/runtime/Git when the evidence packet says that is necessary.

## Safe upgrades

`init --apply` records `.pact/install.json` with file ownership and SHA256 provenance.

- framework-managed files are auto-updatable only when unchanged since install;
- project seed files are never overwritten;
- any true framework conflict blocks the entire automatic apply;
- obsolete framework files are reported but never auto-deleted.

Run upgrade from the newer PACT source checkout:

```bash
python scripts/pact/pact.py upgrade --target ../existing-project
python scripts/pact/pact.py upgrade --target ../existing-project --apply
```

See `docs/design/distribution-upgrades.md`.

## Doctor vs Readiness

- `doctor` answers whether PACT infrastructure/configuration is valid.
- `readiness` answers whether the existing project's baseline was explicitly reviewed.

A freshly scaffolded project should normally be `foundation-valid`, not `pact-ready`.

Use `readiness --require-ready` only when the project has chosen readiness as a gate.

## Pilot evaluation

PACT evaluation is optional and task-based. It tracks dimensions such as owner technical escalations, clarification rounds, false-done prevention, Project Explain recovery, context overload, and optional process overhead.

PACT intentionally does not compute a single 0–100 score.

See `docs/evaluation/pilot-scorecard.md`.

## Safety boundary

`init` is dry-run by default and never overwrites existing files. An existing `AGENTS.md` is preserved; PACT creates merge guidance instead.

The runtime is deliberately hybrid:

- deterministic tooling validates facts it can reliably establish;
- semantic AI review handles meaning, impact, and sufficiency;
- the CLI never promotes heuristic guesses into authority.

Semantic uncertainty should remain a warning, Context unknown, candidate impact, Explanation gap, or Convergence finding.
