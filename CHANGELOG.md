# Changelog

PACT runtime versions track the distributable framework/runtime files used by `pact init` and `pact upgrade`.

They do **not** version a project's Product Truth, Architecture, Decisions, Owner Profile, or other project-owned seed artifacts.

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
