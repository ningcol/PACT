# Blind Query Evaluation — 2026-09-20

This report records a small evaluation of PACT's owner-language to code-language retrieval path.

The question was deliberately narrower than "is PACT retrieval solved?":

> Before adding embeddings or a vector database, can an Agent generate useful code-search hypotheses from the task and pre-change repository context, and can PACT use those hypotheses without losing the owner's primary task Context?

The results are directional evidence from a small sample. They are not a general retrieval benchmark and do not establish semantic-retrieval sufficiency.

## Why this evaluation exists

The historical brownfield replay showed a large gap between direct task wording and curated hindsight vocabulary:

| Metric | Historical replay |
|---|---:|
| Cases | 4 |
| Oracle source files | 18 |
| Direct weighted recall | 0.111 |
| Curated single-expanded weighted recall | 0.556 |
| Curated multi-query weighted recall | 0.667 |

Curated queries are written with hindsight, so they cannot answer whether a real Agent can generate useful vocabulary before implementation. This evaluation therefore froze Agent queries before revealing each historical target diff.

## Evaluation discipline

For blind cases:

1. choose a historical task and pre-change repository state;
2. record the task text and risk;
3. freeze Agent-generated queries before inspecting the target diff/oracle;
4. only then reveal the target commit and mechanically compute changed source files;
5. compare retrieval under equal code-count/token budgets;
6. treat low recall as product evidence, not harness failure.

Post-oracle diagnostics are labeled separately and are never counted as blind results.

## Case 1 — inaccessible target

Repository: `ningcol/xiaohongshu-auto-publish`.

The task/query set was frozen before oracle inspection, but GitHub-hosted runners could not anonymously clone the target repository. PACT Context never ran.

Result: **harness/target-access failure; no retrieval measurement**.

No private credential was introduced merely to make an evaluation pass.

## Case 2 — DouBao watermark-free image download

Repository: `ningcol/DouBaoFreeImageGen`.

- base: `9ca173e37341e4e1a80cadc427737510a3a1eaa5`
- target: `4106e09695d67b3c86e7ca70ca994fc766382503`
- task: `添加无水印下载图片功能`
- risk: medium
- source oracle: `DoubaoMcpBrowserProxy/content.js`

Frozen blind queries:

- `watermark free image download`
- `original image url download`
- `image download handler`

| Arm | Code files | Oracle recall | Selected estimated tokens | Dropped |
|---|---:|---:|---:|---:|
| Direct task wording | 0 | 0/1 = 0.000 | 0 | 0 |
| Blind Agent queries | 3 | 1/1 = 1.000 | 8,051 | 0 |

The blind query set selected:

- `DoubaoMcpBrowserProxy/content.js`;
- `DoubaoMcpBrowserProxy/background.js`;
- `McpServer/server.py`.

This case supports the value of Agent-side vocabulary expansion, but the oracle contains only one source file.

## Case 3 — DouBao debugger/EventStream + Cookie settings

Repository: `ningcol/DouBaoFreeImageGen`.

- base: `f4edad8ea7b49a2f0e92da2aac599350ed042c32`
- target: `9ca173e37341e4e1a80cadc427737510a3a1eaa5`
- risk: medium
- source oracle:
  - `DoubaoMcpBrowserProxy/background.js`
  - `DoubaoMcpBrowserProxy/content.js`
  - `DoubaoMcpBrowserProxy/options.js`

Frozen blind queries:

- `debugger EventStream image URL`
- `clear cookies settings`
- `image extraction debugger`

| Arm | Code files | Oracle recall | Selected estimated tokens | Dropped |
|---|---:|---:|---:|---:|
| Direct task wording | 0 | 0/3 = 0.000 | 0 | 0 |
| Blind Agent queries | 3 | 2/3 = 0.667 | 7,185 | 0 |

The blind queries found `background.js` and `content.js` but missed `options.js`.

A **post-oracle diagnostic**, not part of the blind score, added:

`options settings storage`

That selected four code files, raised estimated materialization from 7,185 to 7,401 tokens, and reached 3/3 oracle recall.

Pre-change `options.js` already contained `saveOptions`, `loadOptions`, Chrome storage, and settings behavior. This suggests the miss was primarily a project-vocabulary-generation gap, not token pressure.

## Case 4 — ziliu Feishu import performance/UX

Repository: `ningcol/ziliu`.

- base: `7542c755ebb0987aeb1415dba2c9f7a71b173993`
- target: `a900bd01d8dcb1098adb151a0eff2a32e908c58b`
- risk: medium
- source oracle:
  - `src/app/api/parse-feishu/route.ts`
  - `src/components/editor/editor-layout.tsx`
  - `src/components/editor/feishu-import-dialog.tsx`
  - `src/components/editor/simple-editor.tsx`
  - `src/lib/services/image-service.ts`

For this case, the Agent was allowed a bounded **pre-change-only** repository structure/vocabulary stage before queries were frozen.

Observed pre-change vocabulary included:

- `FeishuImportDialog`, `processAndImport`, `isProcessing`;
- `/api/parse-feishu`, `processImagesInHtml`;
- `uploadImageFromUrl`, `downloadImage`, `image-service`.

Frozen structure-aware queries:

- `parseFeishuContent processImagesInHtml uploadImageFromUrl`
- `feishu-import-dialog loading progress toast`
- `image-service uploadImageFromUrl retry timeout`

### Before task-primary preservation

| Arm | Code files | Recall | Selected estimated tokens | Important note |
|---|---:|---:|---:|---|
| Direct task Context | 12 | 4/5 = 0.800 | 36,518 | missed `editor-layout.tsx` |
| Structure-aware queries alone | 8 | 3/5 = 0.600 | 39,892 | found `editor-layout.tsx`, lost two direct-task oracle files |
| Task + supplemental fusion | 8 | 2/5 = 0.400 | 39,966 | supplemental fusion displaced useful task Context |

This exposed a product-contract defect: supplemental Agent hypotheses could make high-level Context worse by evicting files already selected from the owner's task wording.

### Fix driven by the evaluation

PR #130 changed high-level task-primary Context semantics:

- task-only selected Context remains canonical;
- supplemental query results may fill remaining capacity;
- generic low-level peer multi-query fusion remains symmetric.

The first attempted weighted-RRF change was rejected because the real reproduction stayed at 0.4 recall and the existing historical multi-query benchmark regressed.

The final #130 design restored the pinned Case 4 task+supplemental result to:

- 12 selected code files;
- 36,518 estimated selected tokens;
- 4/5 oracle recall;
- identical selected paths to the direct task Context.

Historical generic multi-query weighted recall remained 0.667.

### Remaining budget visibility gap

The direct 12-file Context was already at its hard code-count limit. Supplemental retrieval could locate the missing `editor-layout.tsx`, but it could not materialize it without displacing canonical task Context.

A diagnostic on the already-computed fused fallback pool found:

- `src/components/editor/editor-layout.tsx`;
- high-ranked omitted candidate;
- `relation=direct-match`;
- `confidence=direct`;
- retrieval reason includes the frozen Feishu-dialog query;
- estimated materialization cost: 1,588 tokens.

PR #135 therefore added bounded metadata-only `code_candidate_hints`:

- at most five;
- not selected `code_artifacts`;
- no change to selected code ordering;
- no change to hard count or token budgets;
- no addition to selected/materialized token totals;
- no Convergence or completion requirement;
- intended only for selective Agent follow-up.

Pinned Case 4 reproduction retained exactly the same 12 selected paths and 36,518 estimated selected tokens while exposing `editor-layout.tsx` as a hint.

## What the evidence supports

The current evidence supports these technical conclusions:

1. Direct owner/task wording can be insufficient for code retrieval.
2. Agent-generated code vocabulary can materially improve recall.
3. Pre-change repository vocabulary can help the Agent form more project-specific queries.
4. Supplemental queries must not be allowed to silently displace canonical task-selected Context.
5. When Context is already full, a small metadata-only omitted-candidate signal can expose useful follow-up paths without increasing default materialized Context.
6. Existing lexical/graph retrieval can recover some misses once useful project vocabulary is supplied.

## What the evidence does not support

These samples do **not** establish that:

- Agent query generation always produces enough vocabulary;
- PACT now achieves complete recall;
- five fallback hints are universally optimal;
- the current 12-file / 40k medium-risk defaults are globally optimal;
- embeddings or vector retrieval will never be useful;
- PACT reduces owner cognitive load or total engineering time.

The evaluation is deliberately too small to support those claims.

## Current architecture decision

Do **not** add embeddings/vector DB based on the current evidence.

The next retrieval work should prefer:

- project vocabulary and aliases;
- bounded pre-change structure-aware Agent query generation;
- canonical task-intent preservation;
- selective inspection of high-value fallback hints;
- additional real/pinned evaluation samples.

Heavier semantic retrieval should be reconsidered only when new blind evidence shows that useful project vocabulary plus lexical/graph retrieval still cannot expose materially relevant code at acceptable Context cost.
