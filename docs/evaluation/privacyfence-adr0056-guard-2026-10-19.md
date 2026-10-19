# PrivacyFence ADR 0056 source-bound change guard — exploratory engineering check

**Date:** 2026-10-19. **Scope:** PACT repository CI configuration only; external project read-only upstream. **Status:** pending exact-head GitHub Actions run.

## Source and falsifiable prediction (fixed before the CI result)

- Public project: [privacyfence/privacyfence](https://github.com/privacyfence/privacyfence), pinned commit `6a03856a6e1819b2eacd3963154ebc7d02923296`.
- Original policy: `docs/adr/0056-code-carries-no-project-history.md`, Git blob `ba2e6a39df04e373ded03ce2f73d2b1313b6657d`. Accepted ADR requires code comments/docstrings to explain why rather than cite retired plan stages, and original test enforcement.
- Original executable guard: `tests/unit/test_code_no_history.py`, Git blob `ce1102d9a2cab88c149e0b42bb700f3affbdc5c0`.
- **Expected GREEN:** Original upstream tests (existing offline policy/export suite, plus the original code/doc history guards) pass on the immutable upstream checkout.
- **Expected RED:** A second, isolated disposable local clone with the one-line `Phase 42` history marker appended to its tracked `src/privacyfence/__init__.py` is rejected by the unmodified upstream `test_code_carries_no_history`. Require a precise assertion containing source path, `Phase 42` and `phase name` (not just any failure).
- **Source integrity:** The original upstream checkout remains unchanged; check its exact Git commit and clean tracked status. Record original decision and guard blob SHAs. No upstream branches, issues, PRs or files are modified.
- **Evidence:** `.github/workflows/privacyfence-brownfield-pilot.yml` uploads separate actual GREEN/expected RED test logs; exact run URL and outcomes will be attached after CI.

## Interpretation and unresolved gates

This probes a **real source-established decision with a real executable regression guard**; no PACT-authored truth substitutes for the project's ADR. A deliberate invalid code edit is rejected by the upstream guard; this is a useful physical test of an existing decision's durability, **not** evidence that a coding LLM read, correctly retrieved, or obeyed a PACT Decision.

Existing developer-authored source retrieval probe (#225) still observed 30 extraneous current Decision candidates, 2/2 routine injections and approximately 2.16x estimated Context size; this check does not resolve those #221 failures. This exercise is not an independently withheld Agent A/B trial; neither the formal #214 acceptance criteria nor #28 real-Agent, #32 Owner benefit, or #63 release gates can be closed from a green check. No provider credentials, model spending, Owner approval, tags, release or default routing change are involved.
