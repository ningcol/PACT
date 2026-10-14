# Owner-Brownfield Evidence Smoke — ziliu (2026-10-15)

This is a **repeatable machine check** of newly added PACT Evidence/task
helpers against a *real, owner-maintained repository*, but **not** a new
business-feature implementation or proof that the owner's workload decreased.

## Fixed inputs

- Target: [ningcol/ziliu](https://github.com/ningcol/ziliu)
- Historical Git commit: `7542c755ebb0987aeb1415dba2c9f7a71b173993`
- PACT: the exact PR/commit checked out by GitHub Actions, not floating `main`
- Runner: GitHub-hosted Ubuntu, Python 3.12
- Project: fresh isolated Git clone; no production services or credentials
- Workflow: [PACT Owner-Brownfield Evidence Smoke](../../.github/workflows/pact-real-brownfield-evidence.yml)

## Mechanical acceptance

1. Clone the pinned historical project; verify its exact Git HEAD.
2. Adopt current PACT source into the scratch checkout without modifying tracked
   upstream application files.
3. Prepare a medium-risk Task with one explicit observable criterion, and create
   incomplete review drafts.
4. Use `task verify` to check that the historical README has a product overview
   while declaring `README.md` as a repository-local verification source.
5. Confirm that Evidence references AC-1, the run receipt hashes the declared
   README input and the command passed on the inspected workspace.
6. Confirm `task finish` **does not complete** because Convergence and Owner
   Report remain intentionally incomplete, even when one test command passed.
7. Collect a machine-only `pact eval --task` observation. Do not infer any
   human-only metrics.

## What this does *not* prove

The smoke does not install the historical project's npm dependencies, run a
browser, exercise the upstream product's real authorization/data paths, or
observe an owner making decisions. It does not establish semantic equivalence
or portable execution in arbitrary environments. It is a narrow check for
source-bound command receipts and honest refusal of false completion.

Earlier historical task evidence exists in
[the ziliu baseline](real-ziliu-pilot-2026-09-21.md), but the two experiments
do not measure identical phenomena. See [Pilot Scorecard](pilot-scorecard.md)
for the human-required dimensions and baseline comparison discipline.

## Execution evidence

See the workflow run on the proposed PR and rerun it on any PACT change that
touches the guarded task/run/Evidence path. Record the exact successful run
before claiming that this pilot passed. The human decision/overhead and
live-product gates remain explicitly **unverified**.
