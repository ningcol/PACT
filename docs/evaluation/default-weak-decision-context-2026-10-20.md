# PACT default weak-Decision retrieval experiment — frozen plan (2026-10-20)

This is a developer-informed and unblinded engineering experiment. PACT-only changes from exact main 56f581114d0b658bfe25b957d4a2ddd67a5e00d5. No Codex, live model, paid API, upstream repository write, Owner approval or release action.

## Observed baseline BEFORE this proposed change

Frozen public PrivacyFence, privacyfence/privacyfence@6a03856a6e1819b2eacd3963154ebc7d02923296: 10/10 developer-labelled target Decision hits, 30 extraneous selected current-Decision slots across 12 tasks, 6 Decision selections across two routine negatives (2/2), 94,448 estimated Context tokens B. The two-arm A token estimate is different in source content and not a controlled billing comparison.

Frozen public mrwilson/adr-viewer@a25f1c71e031bdaa63fe3175f969f197139f2044: 4/4 developer target hits, 8/8 routine negative tasks selecting unrelated Decisions, 27 extraneous selected slots. Past source-scored receipts identify repeated weak 8/16 point body-only Decision matches. Thus threshold is selected with knowledge of benchmark outcomes, NOT unseen holdout.

## Prospective safe default

On ordinary single-query Context retrieval at risk low/medium, defer only implemented Decisions whose source scorer gives score between 1 and 16 inclusive, with no scored metadata reasons. This means no exact stable ID/title/alias and at most two weak body-term hits. Never apply to high-risk work, history/decision intent, explicit scoped routing, explicit nonfunctional mode, multiple queries, or explicit full-decisions opt-out. Do not alter Discover ranking, confirmed Product Rules, strong current Decisions or historical Decision retrieval.

Deferred candidate IDs, paths, titles, status and source SHA-256 appear in a bounded optional weak_decision_hints Context field. Count/truncation and the warning to inspect source or rerun with full decisions must be explicit. The completion validator and task assist must require Convergence disposition on each deferred source, block source changes and block completion on overflow or malformed metadata. A reduced Context is NOT a finding that those Decisions are semantically inapplicable. High-risk and full-decisions must preserve old source recall.

## Fixed engineering reject gates

1. Frozen PrivacyFence 10/10 positive Decision targets must remain selected, not only hinted. Frozen adr-viewer 4/4 target Decision hits must remain selected. A single regression is a blocker, not a reason to change task wording or the frozen oracle.
2. On the original two PrivacyFence routine negatives, selected current Decision slots must drop below the previous six (with source-hashed deferral metadata). On original adr-viewer negatives, routine cases selecting current Decisions must fall below eight of eight. If not, do not claim default improvement.
3. Hints cannot be forged, overfilled, expired or silently skipped; high risk, history and full-decisions must be unchanged, and task completion/Owner draft must block unreviewed, truncated or stale hints.
4. Full PACT Check, schema/workflow lint, Linux/macOS/Windows × Python 3.11/3.12/3.13, both source-pinned public repository pilot workflows and the real-code engineering pilot must all succeed on the exact commit before merge.
5. Record original and new selected IDs, context estimates and source hashes honestly. Previous frozen oracles, cases and upstream ADR code remain byte-for-byte unchanged. Outcomes are not real Agent obedience, independent blinded holdout, billed model tokens, or measured Owner cognitive load.

If any engineering gate fails, preserve failure receipts and revert the unsafe default; do not close Issue #221 or #214/#28/#32/#63, and keep release HOLD. No additional durable Decision note is justified by this engineering task.
