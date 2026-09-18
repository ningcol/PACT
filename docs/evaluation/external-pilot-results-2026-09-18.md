# External Brownfield Pilot Results — 2026-09-18

This report records PACT behavior on public repositories that did not previously use PACT.

These are **synthetic external pilots**. They validate integration, discovery behavior, upstream verification, and failure boundaries. They do not replace the owner's real-project pilot (#28) or owner-cognitive-load evaluation (#32).

## Summary

| Project | Stack / purpose | Pinned target | Final PACT | Discovery / impact result | Native verification | Completion |
|---|---|---|---|---|---|---|
| FastAPI full-stack template | FastAPI + React + PostgreSQL + Docker | `cb740b656d7a0a6c5e12c7bf8e50343ec94ee9c7` | `38afbdcc55d8ef9bc03a7cf4f76b94d0e9e4f313` | 1 knowledge match, 16 code matches, 24 context code artifacts, 3 impact candidates | Docker Compose build/prestart/start; backend health + frontend HTTP | PASS |
| Flask | mature Python framework | `d73fa1cdcbd8b1465c151db8924ba58b1dd14e35` | `f843ca2f9c7341d6e41621d256c012ac160213c9` | 16 code matches, 24 context code artifacts, 9 impact candidates | 494 pytest tests passed | PASS |
| Pinia | Vue / TypeScript state library | `f4e0cb7a8193f564c27f6527b3f954e114a7534c` | `f843ca2f9c7341d6e41621d256c012ac160213c9` | 9 code matches, 13 context code artifacts, 8 impact candidates; all observed impact edges `relative-resolved` | frozen-lockfile install, typecheck, build | PASS |
| Bubble Tea | Go TUI framework; unsupported code language | `657aaae216e3f87df09b60959a9fe5de7b2ca419` | `f843ca2f9c7341d6e41621d256c012ac160213c9` | 1 knowledge match, 0 target code artifacts, 0 code impact candidates; limitation surfaced explicitly | `go test ./...` passed | PASS |

For every final passing pilot:

- PACT initialization was additive;
- no tracked upstream project file was modified;
- `doctor --strict` passed;
- project-native verification was executed through `pact run`;
- Evidence was source-backed;
- `pact complete` returned `complete=true`.

## Problems found by external projects

### #51 — Markdown link checker false positive

**Found by:** FastAPI full-stack template.

The repository README used GitHub Actions badge routes such as:

`../../actions/workflows/test-backend.yml/badge.svg`

PACT treated any relative link escaping the repository file tree as a broken internal link and failed strict Doctor.

**Resolution:** deterministic link checks now hard-fail only targets that PACT can establish are repository-local and missing. Hosting-platform UI routes outside the file tree are not guessed to be broken.

The exact same FastAPI commit was rerun after the fix and passed end to end.

### #57 — installed PACT scaffold contaminated target Discovery

**Found by:** Bubble Tea unsupported-language pilot.

PACT initially indexed its own installed runtime and generic scaffold as target project knowledge/code. On a Go-only repository, Context incorrectly returned:

- `scripts/pact/impact.py`
- `scripts/pact/risk.py`
- `scripts/pact/schema_validate.py`

This was a serious false-understanding signal.

**Resolution:** Project/Code maps now consult `.pact/install.json`.

- framework-managed PACT paths are excluded from target discovery;
- seed scaffold is excluded while byte-identical to the installed seed;
- once a seed is actually edited by the project, it becomes discoverable;
- a PACT source checkout without an install manifest still indexes itself normally.

The exact same Bubble Tea commit was rerun after the fix. The final result was:

- medium-risk code analysis requested: yes;
- target code artifacts: 0;
- target code impact candidates: 0;
- explicit known unknown for unsupported code understanding: yes;
- Go tests: pass;
- completion gate: pass.

### Pinia harness-only failure

The first Pinia attempt failed before PACT ran because `actions/setup-node` could not cache a lockfile located outside the PACT checkout workspace (`/tmp/pinia/pnpm-lock.yaml`).

This was classified as **pilot harness/toolchain**, not PACT and not Pinia.

The cache configuration was removed; the same pinned Pinia commit then passed twice, including after #57.

## What these pilots support

### Additive adoption is working

Across four unrelated repositories, final PACT adoption did not modify tracked upstream files.

This supports the brownfield safety goal:

> PACT can add control-plane infrastructure without rewriting the existing product merely to adopt PACT.

### Supported-language generated relationships are useful

Python and Vue/TypeScript pilots produced non-empty, task-relevant code context and impact candidates while native verification remained green.

This supports using generated relationships as **candidate context**, not Product Truth.

### Unsupported-language behavior can be honest

After #57, the Go pilot does not fabricate Go code understanding.

PACT still provides:

- repository/doc knowledge discovery;
- risk/completion policy;
- source-backed verification;
- completion gating;

while exposing code-analysis absence as an explicit unknown.

This is closer to the core PACT rule:

> do not turn unsupported inference into certainty.

### External pilots are useful specifically because they fail differently

The FastAPI and Bubble Tea pilots found two PACT bugs that the PACT repository's own test suite did not expose.

That supports keeping external regression workflows as a complementary validation layer.

## What these pilots do **not** prove

They do not establish that PACT has achieved the owner's final goal.

The public repositories did not provide the owner's real:

- business vocabulary;
- long-lived Product Truth;
- historical decisions;
- messy multi-worktree context;
- forgotten business behavior;
- owner decision interactions.

Therefore these pilots do **not** close:

- #28 — real owner brownfield pilot;
- #32 — evaluation using observed owner-project task data.

They primarily validate engineering integration and failure boundaries.

## Repeatable regression

PACT keeps manual GitHub Actions workflows for:

- the FastAPI full-stack deployment pilot;
- Flask / Pinia / Bubble Tea multi-repo pilots.

The workflows accept a PACT ref and pinned target refs so future runtime versions can be checked against the same external baselines without making every normal PACT pull request pay the external test cost.
