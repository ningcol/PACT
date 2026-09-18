# PACT Runtime

The stable v1 entry point is:

```bash
python scripts/pact/pact.py <command> [args...]
```

## Available commands

```text
init       safely scaffold PACT into an existing repository
check      deterministic artifact checks
doctor     PACT repository readiness
audit      deterministic repository health inventory
map        rebuild disposable project map
discover   deterministic project discovery
context    build candidate Task Context Envelope
impact     map changed files to deterministic/candidate project impacts
converge   validate/summarize semantic Convergence Report
evidence   validate completion Evidence Receipt
report     validate and render evidence-backed Owner Report
```

Examples:

```bash
python scripts/pact/pact.py init --target ../existing-project
python scripts/pact/pact.py init --target ../existing-project --apply

python scripts/pact/pact.py doctor
python scripts/pact/pact.py audit --json

python scripts/pact/pact.py discover "batch state"

python scripts/pact/pact.py context "fix province switch" \
  --success "Displayed data follows the selected province" \
  --risk medium

python scripts/pact/pact.py impact --base main --json
```

## Safety boundary

`init` is dry-run by default and never overwrites existing files. An existing `AGENTS.md` is preserved; PACT creates merge guidance instead.

The runtime is deliberately hybrid:

- deterministic tooling validates facts it can reliably establish;
- semantic AI review handles meaning, impact, and sufficiency;
- the CLI never promotes heuristic guesses into authority.

Semantic uncertainty should remain a warning, Context unknown, candidate impact, or Convergence finding.
