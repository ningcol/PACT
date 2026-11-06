# PACT Agent Guide

PACT is the project-level AI control plane for this repository.

Read the version-matched standard instructions with `python3 pact.py guidance`
in a new session and after a runtime upgrade. Use the project-approved Python
interpreter. The repository-specific guidance below remains project-owned;
there is no need to reload the standard guide at every task finish.

When evolving PACT itself, follow the [core-focus and feature-scope guidance](CONTRIBUTING.md#core-focus-and-feature-scope); it is not an extra approval or task step for projects using PACT.

## Constitution

1. Preserve confirmed product truth.
2. Acquire sufficient context before changing behavior; do not read everything by default.
3. AI owns implementation decisions unless they change product meaning, risk acceptance, permissions, irreversible data outcomes, or material cost.
4. Distinguish normative truth (what should happen) from descriptive truth (what currently happens).
5. Verify observable outcomes before claiming completion.
6. Resolve drift by authority; never make product truth follow code automatically.
7. Report to the project owner in product/business language by default.

## Knowledge router

- Governance and authority: `docs/governance/`
- Normative product truth and vocabulary: `docs/product/`
- Current architecture: `docs/architecture/`
- Durable decision rationale: `.agents/decisions/`
- Active/completed change intent: `docs/changes/`
- Drift lifecycle: `docs/drift/`
- Reusable procedures: `.agents/skills/`
- Adoption baseline/readiness: `.pact/baseline.toml`
- System design: `docs/design/system-overview.md`

## Default Agent Surface

Prefer the small task-oriented interface when it is sufficient:

```bash
python3 pact.py status
python3 pact.py inspect "<remembered feature/business behavior>"
python3 pact.py task prepare "<task>" --success "<observable outcome>" --risk <level>
# Add repeatable --accept / --constraint when the task has multiple explicit conditions.
python3 pact.py task draft <TASK-ID>    # optional, explicitly incomplete scaffold
python3 pact.py task verify <TASK-ID> --criterion AC-1 --claim "<specific check>" -- <command>
python3 pact.py task assist <TASK-ID> --json  # optional, read-only diagnostics
# Optional: task assist <TASK-ID> --write-draft fills empty machine fields in a partial Owner Report.
# Review acceptance, Convergence and knowledge retention before marking it completed.
python3 pact.py task finish <TASK-ID>
```

These are default orchestration helpers, not mandatory workflow steps. For explanations or small changes, use proportionate project procedures without automatically preparing a PACT task. Once a Task Contract is prepared, its Evidence and acceptance requirements still apply; use lower-level `discover/context/impact/run/evidence/converge/report/complete` primitives where more precise. Never bypass truth/evidence requirements merely to reduce steps.

## Before changing behavior

For a prepared task, `prepare` captures existing dirty content as its baseline.
Unchanged pre-existing content is excluded from the final-content delta; other
writes in a shared checkout can enter it, and PACT does not identify authors.
Continue with `task status` / `task resume`; `prepare --force` starts a new
baseline including current edits and archives old state for audit without
automatically carrying its Evidence forward; current bindings/provenance still
need verification. Correct manually reviewed bundles may finish directly;
draft/assist are optional and never replace semantic review.

Determine the affected product/domain scope and retrieve only the relevant rules, architecture, decisions, code, tests, and history needed for high confidence.

Do not infer product truth from code alone.

If `pact readiness` reports a baseline area as pending, treat that area as incomplete/unknown rather than manufacturing missing truth.

## Retrieval query expansion

Start with the owner's wording. If relevant knowledge is missing or project
terminology is ambiguous, add only the useful search hypotheses (for example,
a confirmed alias, a likely code symbol, or a state/contract term). Use
repeatable `--query` on `inspect` or `task prepare` when needed.

There is no required query count. Retrieval hypotheses are not confirmed
Product Truth, and guessed vocabulary must never be promoted to authority.

## Decision policy

In adopted projects, ordinary business tasks must not patch framework-managed
runtime files or embedded schemas; use an explicitly authorized PACT maintenance
or upgrade task. Project-owned configuration, knowledge and extensions retain
their existing authority boundaries. See [distribution ownership and upgrades](docs/design/distribution-upgrades.md).

Do not ask the owner to choose implementation patterns, classes, state mechanisms, cache strategies, or other internal engineering choices.

Escalate only when the decision changes product meaning, user-observable behavior, data meaning, permissions/policy, irreversible outcomes, or material risk/cost.

## Completion

A task is not PACT-verified as complete merely because code was written or tests are green. An Owner may explicitly accept a limited delivery with disclosed unverified work under the existing project workflow; that is **not** `task finish` success or `complete=true`, and must not falsify Evidence, waive binding requirements, or silently change a Task Contract. See [Completion Contract](docs/governance/completion-contract.md#owner-accepted-delivery-versus-verified-completion).

Done requires, as applicable:

- implementation complete;
- every Task Contract acceptance criterion verified and owner-visible;
- observable behavior verified;
- every prepared Task Context knowledge artifact explicitly reviewed for convergence;
- relevant truth converged;
- when using a Convergence draft, explicitly resolve its pending knowledge-retention review (normally none for a routine fix, or a justified update/create);
- no unresolved blocking ambiguity;
- evidence exists for completion claims.

## Communication

Before owner-facing explanations, decisions, or completion reports, load the validated Owner Profile:

```bash
python pact.py owner --json
```

Honor its language, technical depth, consequence-first decision translation, and progressive-disclosure preferences. These preferences affect communication, not internal engineering capability.

Owner-facing output should answer:

- What changed for the user/business?
- What was actually verified?
- Is project consistency healthy?
- Is there any product decision the owner must make?

Keep implementation details behind progressive disclosure unless requested.
