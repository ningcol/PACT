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

**Recorded machine results and negative/positive evidence:**

- The [initial isolated assertion](https://github.com/ningcol/PACT/actions/runs/38509795059) **failed** when it required the exact server handler to be *materialized in Context*. This failure is retained as a real relevance observation; it is not silently relabeled as a direct Context hit.
- The [revised selective-follow-up trial](https://github.com/ningcol/PACT/actions/runs/38510025273) **passed** after explicitly checking fallback-hint evidence and consulting the independently ranked `inspect`/`discover` source. It does **not** alter PACT retrieval, promote a candidate rule, or claim source was materialized.
- `pact check`: **PASS, 5 machine-readable temporary knowledge artifacts**. `task prepare --risk medium --code`: succeeded at the exact pinned ziliu HEAD.
- Selected Context: **6 knowledge artifacts** (five pilot artifacts plus README), **12 materialized code artifacts**, **19,384 / 40,000 estimated tokens**. **24 omitted candidates are due to the hard code-count limit**, none due to the token limit.
- Exact `src/app/api/publish/route.ts`: **not** in `code_artifacts`; **present as the second `code_candidate_hints` entry**. The original `inspect` and the exact-path diagnostic both put this path **first** among code results. The agent/test must make a conscious follow-up choice; metadata hints are not selected Context and not Convergence coverage.
- Convergence: 6 required knowledge paths, 6/6 covered; explicitly **`needs-owner`** (a semantically blocking result, correctly validated despite CLI exit 1). No Product Truth was confirmed and no task completion was claimed.
- A static source assertion confirmed four placeholder-success functions; **no runtime POST request, npm test/build, external provider call or production-traffic inspection** occurred.
- Actual owner approval, technical escalation burden, comprehension, saved minutes and overhead metrics: **NOT MEASURED**.

**Review of why initial assertion failed:** The pinned PACT design deliberately preserves task-primary selected materialization before supplemental candidates (`scripts/pact/context.py`, `preserves_task_as_primary` / `compose_primary_preserving_pool`). When the primary result fills the medium-risk count cap, supplemental direct matches become bounded `code_candidate_hints`. This is precisely the documented behavior in [Context Resolver](https://github.com/ningcol/PACT/blob/main/docs/design/context-resolver.md) and the previously resolved [#134](https://github.com/ningcol/PACT/issues/134); reverting primary-task preservation to turn this test green would risk regressing [#129](https://github.com/ningcol/PACT/issues/129).

**Final Stage 2 interpretation:** `PASS_WITH_SELECTIVE_HINT_FOLLOWUP` for the scoped *evidence and owner-authority trial*. The initial materialization miss remains a real limitation and a relevant retrieval-quality observation for #32, not proof of a newly introduced runtime bug. Stage 3 must deliberately include or inspect the API file before implementation. The result does not establish that an unattended agent would always notice or act on the hint.

## 4. Success criteria and stop rule

- Frozen SHA checks and PACT deterministic checks pass; the source is found either in materialized code **or through an explicitly validated non-materialized hint plus a separate direct source inspection**. The initial default-materialization miss remains recorded, not declared a direct hit.
- Candidate/proposed facts remain non-authoritative and selected source evidence is correct.
- Convergence surfaces owner authority as **needs-owner**, while machine coverage is complete.
- Any CI shortcoming is recorded as fail/blocked, not restated as a passing PACT task.
- No ziliu GitHub push, main mutation, publishing side effect or Release.
- Human comprehension, approval choice, clarification rounds, time saved and process overhead remain UNKNOWN until observed, not fabricated.
- **Stop after Stage 2 review.** Stage 3 needs an owner-approved API role, an isolated real HTTP RED reproduction and its GREEN correction. Keep the trial workflow unmerged/temporary and the baseline PR #174 unaffected.

## 5. Future acceptance decision

The concrete product question is: Should \`POST /api/publish\` remain as a supported endpoint that explicitly rejects unimplemented publishing, be retired after proving its consumers, or be separately developed as real provider integration? Technical differences in status codes/DTOs and compatibility will only be fixed after that choice and a caller contract audit.
