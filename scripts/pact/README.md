# PACT Runtime

The stable v1 entry point is:

```bash
python scripts/pact/pact.py <command> [args...]
```

## Available commands

```text
check      deterministic artifact checks
doctor     PACT repository readiness
map        rebuild disposable project map
discover   deterministic project discovery
context    build candidate Task Context Envelope
converge   validate/summarize semantic Convergence Report
evidence   validate completion Evidence Receipt
report     validate and render evidence-backed Owner Report
```

Examples:

```bash
python scripts/pact/pact.py doctor

python scripts/pact/pact.py discover "batch state"

python scripts/pact/pact.py context "fix province switch" \
  --success "Displayed data follows the selected province" \
  --risk medium

python scripts/pact/pact.py evidence .pact/examples/evidence-receipt.example.json
```

## Boundary

The runtime is deliberately hybrid:

- deterministic tooling validates facts it can reliably establish;
- semantic AI review handles meaning, impact, and sufficiency;
- the CLI never promotes heuristic guesses into authority.

A deterministic check may fail CI only when the machine can establish the fact.

Semantic uncertainty should remain a warning, Context unknown, or Convergence finding.
