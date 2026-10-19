# PrivacyFence source-grounded nonfunctional Context alternative (developer-only)

**2026-10-19. Pre-result protocol for PACT PR #229.**
No model calls, Codex, Owner evaluation, independent task custodian, external writes, new default, or long-term Decision creation. Not an independent blind experiment.

## Motivation

#221 records installed retrieval on pinned public `privacyfence/privacyfence@6a03856a6e1819b2eacd3963154ebc7d02923296`, with ten developer-labelled conflict cases and two negative routine cases frozen *before* the earlier scoring implementation. With real source-faithful PACT Decision projections (non-Owner-authenticated), original B retrieved 10/10 target Decisions but had 30 extra current Decision candidate slots, including decisions on 2/2 ordinary no-behavior-change tasks. A+B estimated materialized Context was 43,640 vs 94,448 tokens; this is a CLI estimator, NOT provider-billed usage or observed Agent behavior.

## Narrow prospective alternative

The *original frozen* twelve cards and developer oracle remain byte-identical; the pre-existing A/B evaluator and all 12 outcomes are retained. A separate opt-in B′ runs **only the two original developer-labelled routine tasks**, identical project source and installed code except explicit caller argument `--nonfunctional`. The option is allowed only on low-risk work and demotes source-score non-exact Decisions to at most five **source-hashed metadata navigation hints**, with count/truncation and warning. Exact ID/title/alias Decisions, confirmed Product Rules and ordinary documents remain materializable. It does **not** auto-classify task wording, infer semantic inapplicability, override Owner authority or suppress Decisions on the other ten cases.

**Before seeing B′ outcomes**, record predicted engineering observations: exact original developer-labeled denominator **2/2**; every previously implicit Decision absent from B′ `decisions`, and source-verifiable metadata hints still present; true model calls = **0**; report B′ estimated tokens and candidate counts whether improved or not. If B′ unexpectedly materializes a current Decision, a hint digest is missing/wrong, original tracked sources/projections drift, the installed CLI fails, or any source schema is inconsistent, report **FAIL** with all case-level raw evidence. A lower estimated token count is a measurement, **not** proof of semantic precision, actual model savings, or zero missed applicable constraints. Baseline B remains preserved even if the new probe fails.

## Reproduction

- PACT-owned script: `scripts/benchmark/privacyfence_nonfunctional_probe.py` consumes the **fully finished and source-verified** A/B JSON receipt produced by `scripts/benchmark/privacyfence_pilot.py`. It rejects malformed/failed upstream receipts and compares exactly the two published routine cases; it cannot silently shrink denominators.
- Workflow: `.github/workflows/privacyfence-brownfield-pilot.yml`, two jobs with no secrets, no model or upstream push. Reuse the pinned read-only upstream checkout, run source-identical compact PACT, check frozen ADR blobs and test-only projections unchanged, upload raw developer-labelled baseline and B′ receipts even when the probe fails.
- Core PACT tests: source hashing, schema validation, explicit ID/title/alias preservation, risk/intent fail-closed behavior, task prepare forwarding, and spoofed query-reason rejection. Preserve OS×Python matrix outcomes and full previous defaults.
- Only PACT files may be committed; PrivacyFence never receives a PR or upstream mutation.

## Interpretation and release

This tests **manual source-context materialization**, not any Agent's ability to correctly label a task no-behavior-change. A mislabelled task could still need a weakly matching Decision: the mode warns explicitly to rerun normal Context when behavior/policy/security/Owner meaning may change. Zero deferred full bodies is **not** zero applicable decisions.

Keep #221 OPEN until new independent, unseen retrieval/Agent semantic controls cover false negatives/positives, pathless/Domain decisions, and model/Owner overhead. Keep #214/#28/#32 and release #63 HOLD. Do not approve a default switch, release environment bypass, model credentials or tag from this experiment.
