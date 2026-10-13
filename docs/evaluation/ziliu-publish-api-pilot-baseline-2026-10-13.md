# ziliu Publishing-API Owner-Value Pilot — Stage 1 Baseline (2026-10-13)

**Status:** Stage 1 source-evidence and evaluation design, reviewed separately; **not implemented, executed or owner-approved Product Truth**. This is a candidate real change on the current project, **not** a replay of an already-completed historical patch.

## 1. Immutable inputs and authority boundaries

| Input | Frozen reference |
| --- | --- |
| Pilot product repository | https://github.com/ningcol/ziliu |
| ziliu default branch source | 61af579266848ee50d12a0b658d1e32a49dabfde (2025-12-18 commit) |
| PACT source used to define this plan | 28d8a77e8bbc4fca6db320b4e1a95ac62079385b (after R05 merge) |
| Existing tracked pilot | https://github.com/ningcol/PACT/issues/28 |
| Evaluation track | https://github.com/ningcol/PACT/issues/32 |
| ziliu open Issues / PRs at baseline | 0 / 0 on GitHub (2026-10-13 snapshot) |
| State of current ziliu deployment, credentials, runtime and external platforms | **UNKNOWN / NOT CHECKED** |

Reproduction must use the pinned ziliu commit, not whatever main points at later. First verify the exact Git HEAD and repository identity in a disposable checkout. Do not interpret the age of the last public commit as evidence of the current deployed application version.

**History not to repeat:** The Feishu six-path replay in PR #153 tested a historical patch and initially selected 0 knowledge artifacts. The separate *unmerged* knowledge-layer experiment in PR #156 already selected **4 durable knowledge artifacts + 5 code artifacts** with 4/4 Convergence coverage and preserved candidate/proposed authority. That machine-side result is real; it did **not** measure human owner decisions, comprehension or process cost. The current ziliu main repository does not contain those temporary PACT artifacts.

- Existing six-path pilot: https://github.com/ningcol/PACT/blob/main/docs/evaluation/real-ziliu-pilot-2026-09-21.md
- Follow-up owner-project notes: https://github.com/ningcol/PACT/issues/28

## 2. Selected current task and direct source evidence

**Candidate task:** Correct the false-positive success contract of the existing authenticated server-side publishing API. Determine, with product authority, whether its unimplemented provider operations should fail explicitly, be retired, or become real publishing integrations.

This is grounded in current source, not a claim from an unverified production request.

| Observed source fact | Immutable source evidence |
| --- | --- |
| POST /api/publish requires a NextAuth session and validates title, content, platform, and settings | [route.ts lines 7–40](https://github.com/ningcol/ziliu/blob/61af579266848ee50d12a0b658d1e32a49dabfde/src/app/api/publish/route.ts#L7-L40) |
| Four selected platforms are dispatched to local functions; the outer POST returns success:true irrespective of actual provider acknowledgement | [route.ts lines 49–74](https://github.com/ningcol/ziliu/blob/61af579266848ee50d12a0b658d1e32a49dabfde/src/app/api/publish/route.ts#L49-L74) |
| Knowledge Planet function explicitly constructs synthetic successful per-group results and URL without a provider API call | [route.ts lines 92–126](https://github.com/ningcol/ziliu/blob/61af579266848ee50d12a0b658d1e32a49dabfde/src/app/api/publish/route.ts#L92-L126) |
| WeChat, Zhihu, Juejin local functions each contain TODO and return success:true plus a “feature in development” message | [route.ts lines 129–157](https://github.com/ningcol/ziliu/blob/61af579266848ee50d12a0b658d1e32a49dabfde/src/app/api/publish/route.ts#L129-L157) |
| The inspected editor “Go publish” handler instead prepares content, notifies the extension, copies to clipboard and opens the external publishing page | [platform-preview.tsx lines 474–550](https://github.com/ningcol/ziliu/blob/61af579266848ee50d12a0b658d1e32a49dabfde/src/components/editor/platform-preview.tsx#L474-L550) |

**Scope distinction:** The direct POST API handler and the editor/Chrome-extension workflow are separate paths in the inspected code. Do not assert that the editor calls the POST endpoint, that the existing Chrome extension is broken, or that any live third-party publication has failed. The exact runtime/user impact still needs an isolated RED reproduction and caller audit.

**Confirmed at Stage 1:** the static code fabricates an affirmative API result without checking an external publishing acknowledgement. **Not confirmed:** production routing/traffic, UI usage of this endpoint beyond inspected flow, real provider effects, and live backend status.

## 3. Proposed decision boundary — not a confirmed Product Rule

The candidate business invariant is: “A server-side publishing operation must not be presented as successfully published solely because a placeholder handler returned successfully.”

This invariant is **proposed for owner review**, not silently installed as confirmed Product Truth. The owner should choose the API's intended status:

1. **Preferred bounded fix if approved:** retain the API but report unsupported/not-implemented operations as explicit non-success with truthful error/status, preserving existing auth and input validation. No direct third-party publishing is built.
2. Deprecate/remove the endpoint after checking actual consumers and compatibility risk; preserve the editor/extension path.
3. Authorize full provider integrations in a separate feature project, with credentials/permissions, provider receipts and end-to-end verification. **Not part of this corrective pilot.**

Technical HTTP status, response DTO, potential consumers and compatibility should follow repository conventions and the owner choice; do not invent a normative 501/400/409 contract yet.

## 4. Planned observable acceptance (not yet passed)

- **AC-1:** For each currently simulated platform, an authenticated valid request cannot report successful publication without genuine provider-backed evidence. Knowledge Planet fabricated group URLs/results must not be interpreted as provider receipts.
- **AC-2:** An unauthenticated request still fails with HTTP 401; malformed requests still fail validation (presently HTTP 400). No accidental privilege broadening or unreviewed API contract change.
- **AC-3:** The editor's inspected “Go publish” / clipboard / external page / extension path remains unaffected; no automatic posting, remote account mutation, or external requests occur in test setup.
- **AC-4:** Convergence and Owner Report explicitly distinguish source-verified facts, candidate Product Truth, unresolved owner choice and runtime tests. Without actual publishing evidence they must **not** report a successful real publication.
- **AC-5:** If implementation proceeds, an isolated RED regression must demonstrate the original false-success output first; focused GREEN contract tests, TypeScript and build checks follow on the same pinned/attributed workspace. Any blocked check remains BLOCKED/UNVERIFIED, not PASS.
- **AC-6:** PACT measures observed context volume, scope accuracy, true blockers, verification/evidence completeness, time and owner questions, with no invented human metrics.

Do not equate a passing build or mocked test with third-party delivery.

## 5. Pilot execution design for Stage 2 and beyond

**Stage 2 (separate owner-authorized work):** Create an isolated ziliu checkout at the frozen SHA. Add minimal candidate-domain/rule and proposed-decision knowledge on the isolated pilot branch, each with provenance and non-authoritative status; document current architecture and known drift only from verifiable source. Ask the actual product decision once, rather than silently deciding publishing strategy. Use pinned PACT to discover/inspect, prepare a medium-risk Task Contract with observable acceptance, and capture selected artifacts/known unknowns/token budget. Compare selected Context to a separately reviewed file-level oracle; do not “tune” queries using an already-known final patch.

**Stage 3:** Execute a narrowly scoped source correction only after the owner boundary is resolved. Run isolated, deterministic RED/GREEN endpoint tests with controlled session and provider fakes, then the repository's supported TypeScript/build verification if tooling is available. If the environment requires a remote database, keys, browser extension or third-party service, **do not use production credentials**; report the gate as blocked until an isolated target exists.

**Stage 4:** Generate Evidence, Convergence, Owner Report, final changed-file attribution and PACT task evaluation. Record whether PACT blocked a false “done,” whether Product Truth was respected, and whether the owner was asked only meaningful decisions. Do not promote candidate rule/proposed decision to confirmed/implemented without the applicable authority.

**Stage 5:** Independent changed-file review and reproducible impact/evaluation analysis. Decide whether PACT overhead paid for itself; no automatic framework feature expansion or release.

## 6. Measurement baseline (explicitly unmeasured fields)

| Dimension | Stage 1 value | Future collection method |
| --- | --- | --- |
| Selected project task | API false-success candidate | Revisit once product decision is recorded |
| PACT Context artifacts and estimated tokens on this task | **NOT RUN** | Exact prepared Context/eval receipt, no inferred count |
| Owner product decisions | **UNKNOWN** | Actual owner questions and decisions, count and wording |
| Technical questions escalated to owner | **UNKNOWN** | Record questions that should have been autonomous |
| Clarification rounds / owner comprehension | **UNKNOWN** | Owner-observed iterations and qualitative understanding |
| Human-perceived irrelevant Context / cognitive load | **UNKNOWN** | Direct observation, not a size proxy |
| Implementation and PACT-specific overhead time | **NOT MEASURED** | Timestamped intervals, distinguish ordinary vs PACT overhead |
| Verification runtime, pass/fail, workspace fingerprint | **NOT RUN** | Exact PACT run receipts tied to task workspace |
| Unsupported completion claims blocked | **NOT RUN** | Failed finish/evidence/convergence records; no manufactured failures |
| Actual third-party publishing result | **NOT VERIFIED** | Would require separate approved isolated provider integration |

If a genuinely comparable non-PACT baseline exists, capture it with the same task type, environment and acceptance conditions. Otherwise mark comparisons unavailable; do not fabricate improvement percentages, owner interruptions or time savings. The scorecard does not collapse these dimensions into a single number.

## 7. Stage 1 safety and verification boundaries

- **Reads performed:** public GitHub source/issue/PR/document inspection; no API invocation against ziliu runtime.
- **Writes to ziliu:** none. No branch, Issue, dependency install, database migration, environment read or external publication.
- **Testing:** static source/call-path examination only; no npm, TypeScript, build, CI or PACT lifecycle executed for this candidate.
- **Secrets/production:** no secrets requested, no production endpoint or provider called.
- **Existing PACT historical pilots:** referenced as prior evidence; not rerun or counted as new results.
- **Stage 1 stop rule:** freeze this baseline, review evidence/proposed owner boundary/measurement plan, then pause before a live implementation or owner-dependent promotion.

## 8. Stage 1 independent review checklist

- [x] Candidate source is pinned to an immutable commit with code-line anchors.
- [x] A directly observable unimplemented behavior is present; it is not inferred from a stale README TODO.
- [x] API stub and editor/extension route are distinguished rather than conflated.
- [x] Earlier ziliu durable-knowledge PR #156 was checked; its 4-artifact result is not misreported as zero.
- [x] No human outcome, PACT runtime outcome or live publication is reported without data.
- [x] Owner-level API/product choice is explicit and left unresolved.
- [x] Future verification and stop gates are documented without modifying ziliu.
- [ ] Owner chooses the API's intended role and authorizes Stage 2.
- [ ] Source RED/GREEN, PACT lifecycle, human observations and cost comparison are executed.

**Stage 1 documentation verdict:** evidence-grounded candidate baseline; ready for owner review and separate Stage 2 authorization. **This is not a verified product fix or proof of PACT's owner-value benefit.**
