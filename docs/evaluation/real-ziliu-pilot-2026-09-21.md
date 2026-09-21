# Real Owner-Project Pilot Baseline — ziliu — 2026-09-21

This note records the second machine-observed PACT lifecycle on an owner-maintained brownfield repository.

It is a reproducible historical replay, not proof that PACT reduces owner cognitive load or total engineering cost.

## Reproducible inputs

- Target repository: `ningcol/ziliu`
- Historical base: `7542c755ebb0987aeb1415dba2c9f7a71b173993`
- Historical target: `a900bd01d8dcb1098adb151a0eff2a32e908c58b`
- PACT source head used by temporary pilot: `d096d93c259475f6b043d4dc69deba84f6c7e07f`
- Temporary validation PR: #153
- Task ID: `REAL-ZILIU-FEISHU-001`
- Risk: `medium`
- Task: optimize Feishu import image handling performance and UX

The historical target changes five source files plus `vercel.json`.

## Project baseline vs post-change verification

The pilot installed the pinned project's real npm dependencies with `npm ci`, measured the historical base, freshly adopted PACT, prepared the task, then applied the exact historical Git patch.

| Verification | Historical base | Replayed target |
|---|---:|---:|
| `npx tsc --noEmit` | pass / 0 | pass / 0 |
| `npm run build` | pass / 0 | pass / 0 |

The build completed with existing Next.js metadata warnings on the historical project, but no build failure.

PACT also executed a dedicated historical-replay receipt that mechanically verified the six changed product paths and checked changed file contents against the pinned historical target.

## Context

| Metric | Observed value |
|---|---:|
| Knowledge artifacts | 0 |
| Code artifacts | 8 |
| Known unknowns | 4 |
| Token budget | 40,000 |
| Selected estimated tokens | 39,892 |
| Candidate estimated tokens | 79,226 |
| Dropped candidates | 13 |
| Fallback hints | 5 |

Fallback hints included `src/components/editor/simple-editor.tsx`, one of the historical changed source paths.

This Context was near the medium-risk token budget. The machine data therefore supports further Context-cost evaluation, but does not establish subjective overload.

## Verification

PACT recorded three current-workspace receipts:

1. exact historical replay check;
2. TypeScript verification;
3. Next.js production build.

Machine observation:

- verification runs: 3;
- passed: 3;
- failed: 0;
- runs that changed the workspace: 0.

## Completion integrity

Final successful run:

- Task Contract criteria: 4;
- Evidence verified: 4/4;
- Owner Report covered: 4/4;
- Evidence claims: 3 pass / 0 fail / 0 unverified;
- execution-backed claims: 3;
- workspace-bound claims: 3;
- CI-metadata claims: 3;
- Convergence findings: 0;
- owner decisions: 0;
- completion attempts: 1;
- failed completion attempts: 0;
- final complete: true.

Exact task change attribution found these six paths:

- `src/app/api/parse-feishu/route.ts`
- `src/components/editor/editor-layout.tsx`
- `src/components/editor/feishu-import-dialog.tsx`
- `src/components/editor/simple-editor.tsx`
- `src/lib/services/image-service.ts`
- `vercel.json`

Convergence covered 6/6 changed paths and Final Impact was generated.

PACT-generated state was not attributed as product change.

## A useful blocked false completion

The first temporary-harness run built an invalid completion bundle by guessing Task Contract acceptance numbering instead of reading the prepared contract.

PACT rejected it:

- `task finish` returned 1;
- acceptance summaries did not match the Task Contract;
- two criteria lacked passing Evidence;
- task status remained prepared.

No PACT runtime change was made.

The harness was changed to derive criterion IDs/text directly from the prepared Task Contract, and the same pinned lifecycle then completed successfully.

This is direct pilot evidence that the completion gate can catch an integration-level false completion rather than merely validating a happy path.

## Human-required dimensions still unknown

PACT correctly leaves these dimensions unmeasured:

- owner product decisions;
- technical escalations to the owner;
- clarification rounds;
- owner comprehension;
- subjective Context overload;
- PACT-specific overhead minutes.

This historical replay therefore does not establish reduced cognitive load or lower total process cost.

## What this pilot supports

The evidence supports narrower conclusions:

1. PACT can be freshly adopted into this real Next.js brownfield repository.
2. A real multi-file historical task can pass prepare, exact replay, executable project verification, Evidence, Convergence, changed-file coverage, Final Impact, finish, and eval.
3. Exact task attribution can match a six-file historical product diff without including PACT control-plane state.
4. Completion validation can block a genuinely malformed completion bundle.
5. Context pressure is visible: this sample selected 39,892 estimated tokens and dropped 13 candidates under a 40k medium-risk budget.

## What it does not support

This sample does not establish:

- that PACT lowers owner cognitive load;
- that 40k is the optimal medium-risk Context budget;
- that all eight selected code artifacts were necessary;
- that historical replay equals live end-user/browser validation;
- that Product Truth / Decisions / Owner Profile are sufficiently populated for ziliu;
- that one successful multi-file replay generalizes to all repositories.

## Next evaluation work

The next owner-project work should focus less on another identical replay and more on the gaps that remain:

- capture human-required owner/clarification/overhead observations;
- exercise durable Product Truth / Decisions rather than a Context with zero knowledge artifacts;
- evaluate a task requiring a real owner product decision;
- evaluate changed-file proximity only where changed paths are legitimately known before Context resolution (#138).

Do not collapse this pilot into one PACT score.
