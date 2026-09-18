# Brownfield Historical Retrieval Benchmark

This benchmark measures one narrow question:

> Before a real historical change was implemented, could PACT Context retrieval locate source files that the later real commit actually changed?

It is deliberately **not** a coding-agent benchmark and **not** proof that the owner can stop reviewing engineering work.

## Oracle

Each case records:

- a real repository;
- a pre-change `base_commit`;
- the later real `target_commit`;
- a historical task proxy reconstructed from the commit message unless another source is explicitly recorded;
- an optional curated expanded search query used as a post-hoc diagnostic.

The harness computes the oracle mechanically from:

```text
git diff --name-only base_commit target_commit
```

It keeps only source families that the current PACT Code Map supports and only files that already existed at the base commit. Newly-created source files are reported as unavailable-at-base rather than counted as retrieval misses.

## Two retrieval modes

Every case is replayed twice.

### Direct

PACT receives the task proxy as the discovery query.

This measures the current high-level surface against a repeatable historical description, but it is **not** a reconstruction of the exact original owner prompt unless a case explicitly provides one.

### Curated expanded diagnostic

The task remains unchanged, but the query is manually expanded with likely code/business vocabulary.

The initial expanded queries are curated with hindsight from the historical change. They are therefore an **upper-bound diagnostic**, not an unbiased measurement of what an Agent would have generated before implementation.

This diagnostic answers a narrower question:

> If the Agent can supply better vocabulary, is lexical + graph retrieval already sufficient enough to improve recall?

If curated expansion materially improves recall, that is evidence to test automatic query expansion before adding embeddings or a vector database. If it does not, query expansion alone is unlikely to solve the retrieval gap.

The expanded query and its provenance are stored with each benchmark case so the benchmark remains repeatable.

## Metrics

Per case:

- oracle source file count;
- Context code artifact count;
- matched/missing oracle files;
- rank of matched oracle files;
- retrieval recall;
- a precision proxy;
- known-unknown count.

The precision value is intentionally called a **proxy**. Files outside the historical diff can still be valid Context, so `matched / context-size` is not semantic precision.

Aggregate output includes weighted direct/curated-expanded recall and the number of cases improved by the curated diagnostic.

## Failure semantics

Low recall does **not** fail the benchmark.

A low score is useful product evidence.

The workflow fails only when the benchmark harness cannot execute a case correctly, for example:

- repository/commit cannot be checked out;
- PACT cannot initialize;
- Context generation crashes;
- historical diff has no usable oracle source file.

This prevents optimizing PACT merely to satisfy an arbitrary benchmark threshold.

## Initial cases

The initial replay set uses real historical tasks from owner-maintained public brownfield repositories:

- `ningcol/MultiPost-Extension`;
- `ningcol/ziliu`.

The cases cover:

- platform publishing behavior;
- cross-file TypeScript contract fixes;
- editor state persistence;
- style preservation across a publishing pipeline.

Private or unsupported-language projects can be added later when the benchmark infrastructure proves useful.

## Running

```bash
python scripts/benchmark/historical_replay.py
```

One case:

```bash
python scripts/benchmark/historical_replay.py \
  --case ziliu-editor-state-persistence
```

The GitHub Actions workflow runs the same harness and publishes the result to the workflow summary.

## Relationship to real Owner evaluation

Historical retrieval answers:

> Did PACT retrieve useful code context?

Real task evaluation (#32) must still answer:

- how many technical questions reached the owner;
- how many product decisions genuinely required the owner;
- whether completion claims were false or blocked;
- whether the owner understood the result;
- process/time/token cost.

Do not use this retrieval benchmark as a substitute for those measurements.
