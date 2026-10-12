# Impact Analysis

PACT Impact Analysis answers:

> Given these changed files, which project knowledge is definitely connected, which areas are plausible candidates, and which changes remain unmapped?

The v1 model is intentionally conservative.

## 1. Deterministic impact

A relationship is deterministic only when the repository explicitly encodes it.

Examples:

- the changed file is itself a PACT artifact;
- a Domain declares a path glob that matches the changed file;
- an artifact explicitly links to the changed path;
- a Product Rule explicitly names the changed file as a verification target;
- a changed text file explicitly references a Stable ID.

### Markdown link path semantics

For an explicit Markdown link, Impact resolves its destination relative to the directory containing the Markdown document. For example, a link in `docs/product/rules/password.md` to `../../../src/api/reset.py` identifies the repository file `src/api/reset.py`. A nested document's link to `src/api/reset.py` means a sibling-relative path, **not** the repository root's `src/api/reset.py`.

Leading-slash Markdown destinations are interpreted from the repository root, matching PACT's own link checker. URL fragments, query strings and percent-encoded path components are normalized when identifying the file. External URLs and paths that escape above the repository root are not counted as deterministic file relationships.

This applies only to explicit Markdown destinations. The `verification` and declared domain-path metadata fields remain repository-relative by their existing contract. These checks establish that a textual link exists and points to the selected path, not that the target implementation is semantically correct.

Deterministic means:

> the relationship exists.

It does **not** automatically mean:

> the behavior is broken.

## 2. Candidate impact

Candidate impact is useful context that still needs semantic review.

v1 candidates include:

- artifacts sharing an explicitly impacted Domain;
- artifacts referenced through `related` metadata.

Candidate impact must never become a hard CI failure merely because the relationship exists.

## 3. Unknown changes

A changed file with no deterministic relationship is returned as unmapped.

That is not an error.

It tells the Agent:

> PACT has no explicit semantic mapping for this file; use code analysis, Project Discovery, Git history, or runtime evidence to expand context.

## 4. Sparse semantic path ownership

Important Domains may optionally declare code/document path globs:

```yaml
pact:
  type: domain
  id: DOMAIN-BATCH
  paths:
    - src/features/batch/**
    - src/api/batch/**
```

Do this only for durable, high-value boundaries.

Do not try to manually map every file in the repository.

## 5. Output

`pact impact` emits:

- changed files;
- deterministic relationships;
- candidate relationships;
- impacted Domains;
- unmapped files.

This output feeds Context Resolution and Convergence; it is not itself normative truth.
