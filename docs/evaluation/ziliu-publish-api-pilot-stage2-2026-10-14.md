# ziliu publishing-API PACT pilot — Stage 2 caller audit and owner-authority gate (2026-10-14)

**Stage:** Separate from [Stage 1 Draft PR #174](https://github.com/ningcol/PACT/pull/174). Pinned PACT baseline: main at 28d8a77e8bbc4fca6db320b4e1a95ac62079385b; pinned public ziliu source: 61af579266848ee50d12a0b658d1e32a49dabfde. Stage 2 changes only this report and a temporary PACT CI workflow; it makes **no ziliu repository changes**.

## 1. Exhaustive tracked text-source caller audit (GitHub snapshot)

Read the complete non-truncated GitHub tree at pinned ziliu main and individually inspected all **132 tracked .ts/.tsx/.js/.jsx/.mjs/.cjs/.md files** with no failed fetches. A literal-match scan looked for:

- \`/api/publish\`
- \`publishToWechat\`, \`publishToZhihu\`, \`publishToJuejin\`, \`publishToZsxq\`
- single-line fetch/axios publishing references and \`platform/publish\`
- supporting \`chrome.runtime.sendMessage\` evidence

**Result:** the only direct \`publishTo*\` symbols in this scan were definitions/dispatch within [src/app/api/publish/route.ts](https://github.com/ningcol/ziliu/blob/61af579266848ee50d12a0b658d1e32a49dabfde/src/app/api/publish/route.ts). No literal \`/api/publish\` consumer was found in the inspected tracked source. The current editor's [handlePublish](https://github.com/ningcol/ziliu/blob/61af579266848ee50d12a0b658d1e32a49dabfde/src/components/editor/platform-preview.tsx#L474-L550) notifies the extension, copies content and opens an external page; browser plugin modules, including the Knowledge Planet adapter, contain separate publishing behavior.

**Coverage limitation:** this is a lexical scan of the enumerated source families, not a dynamic call graph, full transitive consumer proof, runtime network trace, compiled/deployed artifact audit or third-party integration census. Dynamic paths, unseen clients, production traffic and undeclared integrations remain UNKNOWN. It does not prove the endpoint is safe to delete.

## 2. Confirmed code problem versus unapproved business intent

[POST route.ts lines 49–74](https://github.com/ningcol/ziliu/blob/61af579266848ee50d12a0b658d1e32a49dabfde/src/app/api/publish/route.ts#L49-L74) returns outer \`success: true\` for all four selected platform handlers. [Lines 92–157](https://github.com/ningcol/ziliu/blob/61af579266848ee50d12a0b658d1e32a49dabfde/src/app/api/publish/route.ts#L92-L157) construct synthetic success for ZSXQ and return success from TODO placeholder methods for WeChat, Zhihu and Juejin. This is verified **static code evidence**, not an HTTP runtime test or production user report.

The product boundary must remain explicit: the owner may approve (A) bounded fail-closed placeholder responses while retaining the API (recommended as lowest-risk corrective direction pending compatibility audit), (B) safe deprecation after external caller investigation, or (C) a separately-scoped real provider integration. None of these is treated as already owner-approved Product Truth.

## 3. Isolated machine trial: candidate knowledge and genuine owner blocker

The adjacent **temporary GitHub Actions workflow** operates only within an ephemeral CI checkout and:

1. Clones public ziliu and verifies the exact frozen commit. No product repo branch or remote production target is mutated.
2. Adopts the current PACT runtime into that checkout, creating temporary \`candidate\` Domain and Rule, \`proposed\` Decision, \`current\` source-verifiable Architecture, and \`known\` drift/verification gap.
3. Runs PACT deterministic checks, indexing/inspect, and a medium-risk \`task prepare --code\` with explicit task language and independent technical queries.
4. Requires the selected Context to contain the candidate publishing Rule and real \`src/app/api/publish/route.ts\` implementation.
5. Validates Convergence coverage across selected knowledge while intentionally issuing a blocking \`owner-decision\` finding; accepts **\`needs-owner\` as the correct result**, not a false success.
6. Emits machine Context paths/counts/token estimates without inventing any human-observed metrics.

**Tooling and safety:** no ziliu \`npm ci\`, database migrations, remote publish call, third-party account, privileged token, browser session or production state. A lightweight source assertion is static, **not** a RED HTTP response reproduction, not a GREEN implementation, and not an E2E success claim.

**Observed CI results (run on pinned ziliu and PACT):**

- [Isolated pilot run](https://github.com/ningcol/PACT/actions/runs/38509795059): **FAIL** at the intentional Context-target selection assertion. This is a meaningful negative test, **not** a green PACT task.
- Deterministic PACT `check` PASS: 5 temporary knowledge artifacts were accepted. Medium-risk `task prepare` succeeded.
- Context selected **6 knowledge artifacts** (5 candidate/proposed/current/known pilot items plus README) and **12 code artifacts**, but **did not select `src/app/api/publish/route.ts`** despite an explicit technical query.
- `inspect` surfaced that same route as its **top code result**; an exact-path `discover` also returned it first. `Context.code_candidate_hints` included the route (second hint), but hints are **not materialized code artifacts**.
- **19,384 / 40,000 estimated Context tokens** were used; **24 candidates were dropped for the 12-file count cap**, zero for token budget. This is a count/ranking interaction, not token exhaustion.
- Convergence separately checked all **6/6 knowledge artifacts** and correctly returned `needs-owner` because the API's product policy is unsettled. That is not a completion success or proof of a real publication.
- No ziliu application tests or HTTP runtime RED/GREEN tests ran. Human owner-value metrics remain `NOT_MEASURED`.

**Reproducible source-level mechanism for follow-up review:** High-level `task prepare` prepends the natural-language task as the primary query (`scripts/pact/task.py`). The `context.py` code path `preserves_task_as_primary` / `compose_primary_preserving_pool` puts up to the full primary selection before fused supplemental candidates; `select_context_candidates` enforces the 12-file count cap. At this fixed task wording, generic API-path matches fill all code slots even though the supplemental technical query correctly finds the target. Preserving owner-language task intent is an existing deliberate design invariant, so simply disabling it is **not** an acceptable speculative fix.

**Stage 2 decision:** This trial establishes a real, narrow **Context relevance miss** and a working owner-decision blocker. The Context-selection acceptance is **NOT SATISFIED**; the stage is `CHANGES REQUESTED` for retrieval, not PASS. A subsequent corrective stage should preserve task-primary context intent while ensuring strongly grounded supplemental code is not silently excluded under a saturated code cap; prove this against both this frozen case and historical no-regression cases. Do not weaken existing acceptance or inflate the token/code budgets merely to turn the check green.

## 4. Success criteria and stop rule

- Frozen SHA checks and PACT deterministic checks pass; the **separate** relevant-code selection gate currently fails and is retained as an explicit negative result.
- Candidate/proposed facts remain non-authoritative and selected source evidence is correct.
- Convergence surfaces owner authority as **needs-owner**, while machine coverage is complete.
- Any CI shortcoming is recorded as fail/blocked, not restated as a passing PACT task.
- No ziliu GitHub push, main mutation, publishing side effect or Release.
- Human comprehension, approval choice, clarification rounds, time saved and process overhead remain UNKNOWN until observed, not fabricated.
- **Stop after Stage 2 review.** Stage 3 needs an owner-approved API role, an isolated real RED reproduction and its GREEN correction. Keep the trial workflow unmerged/temporary and the baseline PR #174 unaffected.

## 5. Future acceptance decision

The concrete product question is: Should \`POST /api/publish\` remain as a supported endpoint that explicitly rejects unimplemented publishing, be retired after proving its consumers, or be separately developed as real provider integration? Technical differences in status codes/DTOs and compatibility will only be fixed after that choice and a caller contract audit.
