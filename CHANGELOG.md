# Changelog

PACT runtime versions track the distributable framework/runtime files used by `pact init` and `pact upgrade`.

They do **not** version a project's Product Truth, Architecture, Decisions, Owner Profile, or other project-owned seed artifacts.

## Unreleased

Development runtime on `main`: `0.4.0-dev.1`. No `v0.4.0` release has been published by this change.

### Minimal Adoption / Lazy Materialization

- fresh brownfield installs use one compact control-plane surface;
- initial adoption installs only the executable/control-plane nucleus instead of empty Product/Architecture/Decision/Change/Drift/Skill scaffold;
- optional durable knowledge locations may remain absent until real project knowledge needs to be preserved;
- adopted-project Doctor validates the minimal executable nucleus without treating absent lazy knowledge directories as broken;
- the default Agent task trust loop remains in compact `AGENTS.md` / merge guidance, so removing empty Skill scaffold does not weaken Task Contract, Evidence, Convergence, Owner Report, or completion requirements;
- upgrades preserve the compact installed surface without alternate legacy/full profiles;
- existing `AGENTS.md` remains untouched and receives merge guidance under `.pact/`;
- real DouBaoFreeImageGen historical fresh-adoption validation reduced the install from the original 97 managed files to 8 managed files (9 physical files including `.pact/install.json`) while strict Doctor, Status, schema-lint, and code-aware Task Context still passed.

### CI efficiency

- PACT Check remains the single full correctness gate and still runs every unit test;
- the 3×3 Core Matrix now focuses on cross-platform bootstrap/runtime/distribution/stdlib/init/Git-path portability instead of repeating the complete semantic test suite nine times;
- release validation still runs the full unit suite.

### Pre-release simplification

- removed unreleased legacy YAML config/front-matter parsing;
- removed alternate legacy/full install profiles and runtime compatibility shims;
- run receipts now use only the current workspace-bound format;
- prepared tasks must carry the current Context SHA contract;
- upgrade tests now cover current-runtime update/conflict/rollback/seed safety instead of unreleased migration paths.

### Release / distribution hardening

- bootstrap ZIP extraction now limits archive file count, per-file expanded size, total expanded size, local archive size, and suspicious compression ratios before extraction;
- tag releases are blocked on the same 3 OS × 3 Python portability coverage used for normal development;
- normal PR CI and tag publication now use the same release-asset builder and run a fresh offline bootstrap smoke against the exact `pact-bootstrap.py` / `pact.pyz` / `SHA256SUMS` package before publication;
- prerelease version suffixes publish as GitHub prereleases instead of stable releases while exact tag/VERSION equality remains required;
- non-Git high-level task completion now surfaces that exact changed-file attribution is unavailable instead of silently providing a weaker guarantee;
- stale version-specific Python requirement messages were replaced with the protocol-level Python 3.11+ requirement.

### Reliability hardening

- `task status` now reports completion files from the task manifest's actual `completion_bundle`, including custom relative/absolute bundle paths, instead of always assuming the default `.pact/completions/<TASK-ID>` location;
- `task finish` now atomically publishes completion-attempt history and stages Final Impact before replacing its canonical path, so persistence failures preserve prior valid derived state and do not follow leaf symlinks;
- `pact init --apply` now rejects parent-directory symlink escapes and treats existing leaf symlinks, including broken symlinks, as occupied paths under no-overwrite semantics;
- `pact upgrade` now applies the same repository confinement during planning/provenance reads, rejecting symlinked install manifests and framework-managed leaf symlinks before hashing or mutation;
- non-Git workspace fingerprints now include directory symlink identity/target without traversing linked directories, so retargeting invalidates workspace-bound Evidence;
- Project Map / Code Map file enumeration now refuses file symlinks whose resolved content escapes the repository root, preventing external files from being indexed as project knowledge;
- `pact init --apply` now stages all would-be-created files before target mutation, publishes them atomically, commits install provenance last, and rolls back transaction-created files/manifest state on failure;
- Project Map and Code Map freshness fingerprints now include source-content SHA256 instead of relying on size/mtime;
- per-file parse cache reuse is content-hash bound, so equal-size content replacements with preserved mtimes are reparsed;
- `pact run` streams stdout/stderr while hashing instead of retaining full command output in memory;
- validated `pact run` receipts are staged in the destination directory, fsynced, and atomically published so interrupted/failed writes do not leave partial receipts or follow a pre-existing leaf symlink;
- interrupted `pact run` execution now terminates its direct verification child with bounded terminate/kill cleanup, returns controlled status 130, and avoids publishing a receipt or leaking a Python traceback;
- Git workspace fingerprint V2 hashes staged index state, current unstaged file state, and untracked contents instead of buffering full binary patches;
- large-output and large-binary workspace regressions now run in the cross-platform portability matrix.

### Trust hardening batch

- prepared task risk is bound through Context/Evidence/completion so a high-risk task cannot be downgraded by editing Evidence risk;
- task IDs use one safe path-segment protocol and are confined before task/run/eval filesystem access;
- run receipts enforce exit-code/status consistency;
- local receipt terminology distinguishes execution-backed/workspace-bound provenance from tamper-proof attestation; GitHub Actions fields are CI metadata only;
- malformed or unsafe install manifests fail closed;
- locally modified framework-managed files block automatic upgrade instead of leaving stale framework ownership;
- high-level task preparation runs deterministic repository checks before Context creation;
- Owner verification claims cannot expand referenced Evidence claims, and Convergence Evidence IDs must resolve.

### Evidence trust hardening

- repository file provenance is static/source evidence and no longer counts as executed verification;
- medium/high required pass claims need a passing `pact-run` receipt bound to the current workspace;
- Evidence refs are confined to the repository root after path/symlink resolution;
- low-risk claims may still use static repository evidence when that level of proof is appropriate.

### Daily status / readiness UX

- normal `status` treats pending repository-wide baseline review as advisory instead of permanent warning state;
- `readiness --require-ready` remains the explicit opt-in full-baseline governance gate;
- malformed/invalid baseline readiness now blocks `status` rather than being silently downgraded;
- `status` reuses its Doctor result when evaluating readiness instead of invoking Doctor twice;
- Doctor persists the freshness-aware Project Map used for its check, and `status` reuses that same map/check result for the audit summary instead of rescanning the repository.

### Task-state UX / atomicity

- fresh init uses nested `.pact/.gitignore` instead of touching the project root `.gitignore`;
- cache/tasks/runs/completions/tmp are explicit local generated control-plane state;
- `task prepare` stages all preparation artifacts under `.pact/tmp` and atomically publishes the task only after Context/Impact succeed;
- task/completion state IDs must resolve to real direct children rather than symlink/junction aliases;
- canonical `task.json` reads reject leaf symlinks, and task manifest updates are staged, fsynced, and atomically replaced so interrupted finish writes preserve the previous recoverable state;
- failed preparation leaves no half-created visible task;
- `--force` preserves the old task/completion until replacement preparation succeeds, then invalidates stale completion state.

### Retrieval / Context

- high-level `task prepare` now preserves the task wording as primary retrieval intent and treats repeatable `--query` values as additional search hypotheses, matching recommended `inspect` behavior;
- task-primary Context selection now preserves the files selected by the owner/task wording under the same count/token budgets before supplemental Agent queries fill remaining capacity; peer low-level multi-query fusion remains symmetric;
- task-primary Context may expose up to five metadata-only `code_candidate_hints` for high-ranked fallback code paths that did not fit the selected canonical Context; hints do not change selected artifacts, token accounting, or completion coverage;
- Python Code Map structured symbols now include direct class methods (without recursively indexing local nested functions), and generated Code Map/parse-cache versions are bumped so existing caches rebuild under the new retrieval semantics;
- Code Map adds a bounded `generic-lexical` fallback for Go, Swift, Kotlin, Java, Rust, C/C++, C#, Ruby, and PHP;
- generic fallback stores at most 256 lexical identifiers per file and creates no import/AST edges;
- generic identifier matches rank below structured top-level symbols and remain derived search evidence only;
- recommended `inspect` now accepts repeatable retrieval queries and forwards the same normalized query set to explanation knowledge and code discovery;
- `inspect --code-limit` provides a hard final code-candidate budget;
- Explanation Packets record the actual retrieval query set used;
- inspect/explain now propagate indexing/discovery failures instead of downgrading nonzero JSON child exits to empty results;
- `code_limit` is now a true final output budget for both single- and multi-query retrieval;
- query-diverse fusion prevents specialized query intents from being silently starved when the budget permits representation;
- historical retrieval comparison now enforces equal final code budgets across direct/expanded/multi-query modes;
- Context adds a soft risk-adaptive estimated materialization-token budget on top of hard artifact-count limits;
- token estimates use deterministic repository file size (`UTF-8 bytes / 4`) and never materialize file bodies into the Context envelope;
- confirmed Product Rules and implemented Decisions may explicitly exceed the soft token budget instead of being silently dropped;
- `discover`, `context`, and `task prepare` accept repeatable discovery queries;
- multi-query retrieval uses deterministic Reciprocal Rank Fusion across independent lexical/graph result lists;
- fused multi-query Context is capped by the existing risk-adaptive knowledge/code limits;
- Task Context records the actual `discovery_queries` used;
- Agent guidance now treats expanded queries as search hypotheses rather than project truth;
- the historical brownfield benchmark compares direct, single-expanded, and fused multi-query retrieval.

### Compact Runtime

- adopted projects use one `.pact/pact.pyz` runtime behind the stable repository-root `pact.py` entry point;
- framework JSON schemas are embedded in `pact.pyz` and no longer copied into adopted projects;
- compact runtime schema resources are authoritative over preserved obsolete local schema files;
- `schema-lint` validates the full embedded protocol set in compact installs;
- safe upgrade removes unchanged obsolete source-runtime/schema files with rollback, while preserving local modifications.

### Convergence Trust

- prepared tasks record a Git-aware workspace baseline without requiring a clean worktree;
- `task finish` derives the files whose final content changed relative to preparation, excluding generated PACT state;
- actual task-changed files automatically feed a final Impact report;
- Convergence `change_coverage` must review every task-changed path; missing/duplicate/stale coverage blocks completion;
- pre-existing dirty files are not attributed to the task unless their content changed after preparation;
- prepared Task Contexts now carry SHA256 binding into high-level completion;
- selected knowledge artifacts carry prepared content fingerprints when available;
- Convergence Reports can explicitly dispose every Task Context knowledge artifact;
- `task finish` blocks silent Context omission and stale prepared Context reuse;
- `updated` artifact dispositions are rejected when the prepared artifact content did not actually change;
- machine task observations record Convergence coverage blockers.

### Evaluation / proof of value

- machine task observations now include Context token-budget pressure, task changed-file attribution/final Impact, and changed-file coverage blockers;
- `pact eval --all-tasks --json` derives all valid local task observations and summarizes machine-only trust/context/verification metrics overall and by risk;
- malformed local task state is reported explicitly in the machine summary instead of being silently omitted;
- machine summaries deliberately do not infer owner interactions, comprehension, subjective overload, PACT overhead, or a single PACT score;
- high-level `task finish` persists completion-attempt outcomes for later evaluation;
- `pact eval --task <TASK-ID>` derives machine-observed task metrics without fabricating human-interaction values;
- added a real historical brownfield Context-retrieval benchmark using owner-maintained repositories;
- benchmark compares direct owner-language retrieval with Agent-expanded queries and treats low recall as data, not a CI failure.

### Owner Trust Loop

- `task prepare` now persists a machine-readable Task Contract;
- repeatable acceptance criteria receive stable `AC-*` IDs;
- Evidence claims can bind directly to acceptance criteria;
- `task finish` blocks completion when acceptance is unverified or omitted from the Owner Report;
- task-scoped constraints and acceptance coverage are visible through the high-level task surface.

## 0.3.0 — 2026-09-18

PACT 0.3 focuses on reducing adoption friction and hardening the trust boundary between AI claims and real project state.

### Zero-dependency runtime

- removed PyYAML and jsonschema runtime dependencies;
- removed `scripts/pact/requirements.txt`;
- PACT core now requires only Python 3.11+ standard library;
- added internal validation for the JSON Schema subset used by PACT;
- added repository-root `pact.py` convenience entry point.

### TOML and compatibility

- new project config, baseline, and fitness files use TOML;
- new PACT Markdown artifacts use TOML front matter;
- PACT 0.2-generated YAML remains readable through a restricted compatibility parser;
- legacy Owner config and baseline state are normalized during 0.3 use;
- Domain aliases are now machine-readable and actually consumed by Discovery;
- Decision template is now a real machine-readable PACT Decision artifact;
- readiness now includes explicit `agent_bootstrap` review.

### Trusted completion

- added `pact run` command receipts with real argv, exit code, timestamps, Git state, and stdout/stderr hashes;
- Evidence now carries explicit provenance;
- medium/high-risk required pass claims need machine-backed evidence;
- Owner Reports cannot describe failed/unverified Evidence as verified;
- Evidence, Convergence, and Owner Report bind to the same task ID;
- added `pact complete` to validate the full completion bundle;
- high-risk completion blocks unresolved Evidence limitations and non-aligned Convergence.

### Risk and discovery freshness

- low/medium/high risk now changes default Context depth and code expansion;
- medium/high Impact Analysis enables code-neighbor analysis by default;
- Project Map and Code Map now use source fingerprints and rebuild only when stale;
- Explain/Context/Impact share freshness-aware caches;
- generated code relationships expose confidence instead of pretending all import resolution is equally certain.

### Deployment

- added stdlib-only single-file `bootstrap.py` for init/upgrade without cloning PACT;
- bootstrap supports pinned GitHub refs/commits and optional archive SHA256 verification;
- bootstrap rejects archive traversal and symlink entries;
- fixed mixed-version `init` behavior: tracked projects on another runtime must use upgrade;
- legacy YAML project seeds are preserved rather than shadowed by default TOML files;
- upgrades now stage/verify replacements, back up targets, atomically replace files, and rollback files + install manifest after apply/validation failure;
- strict Doctor validates framework-owned file hashes against install provenance.

### Still intentionally open

- real brownfield pilot (#28);
- evaluation using observed real-project task data (#32).

These remain open because framework implementation is not evidence that PACT improves real project work.

## 0.2.0 — 2026-09-18

### Added

- tracked installation provenance in `.pact/install.json`;
- transactional, conflict-aware framework upgrades;
- explicit framework-managed vs project-seed ownership;
- runtime version inspection;
- generated Python / JavaScript / TypeScript / Vue code maps;
- opt-in code-aware Project Discovery;
- opt-in code-aware Task Context;
- import-neighbor Impact candidates;
- pluggable project-owned Architecture Fitness Functions;
- optional real-task Pilot Evaluation records and summaries.

### Changed

- Context Resolution promotes only confirmed Product Rules and implemented Decisions into authoritative task constraints;
- Doctor validates install provenance and project Fitness configuration without implicitly running architecture checks;
- project CI can run Fitness explicitly while keeping application build/test/E2E commands project-owned;
- code relationships remain generated/disposable evidence rather than project truth.

### Safety

- project seed files are never silently overwritten by runtime upgrade;
- local/upstream conflicts in framework-managed files block automatic upgrade before any partial update;
- unresolved path aliases/framework magic are reported as unresolved rather than guessed;
- structural import relationships are treated as candidate behavioral impact, not hard product truth.

## 0.1.0 — 2026-09-18

Initial executable PACT v1 foundation:

- Governance / Truth Ownership / Decision Authority;
- brownfield-safe initialization;
- explicit baseline readiness;
- Owner Profile and Human Interface contracts;
- Project Discovery and Project Explanation;
- Context Resolution and conservative Impact Analysis;
- Evidence Receipts and evidence-backed Owner Reports;
- Convergence Reports;
- deterministic artifact/reference/lifecycle checks;
- Doctor / Audit;
- opt-in project GitHub Actions integration.
