# Project Discovery Model

Project Discovery answers:

> I remember the feature, behavior, page, or reason — but not the file. Where is the relevant project knowledge?

It is intentionally different from Context Resolution:

- **Discovery** locates the project concept and its knowledge neighborhood.
- **Context Resolution** decides how much of that neighborhood a specific task needs.

## 1. Discovery pipeline

```text
natural-language query
        ↓
canonical vocabulary / aliases
        ↓
ranked project artifacts
        ↓
stable IDs + related domains
        ↓
rules / architecture / decisions / changes / code-entry hints
        ↓
context packet
```

## 2. Derived index, never authority

PACT may build `.pact/cache/project-map.json` for fast lookup.

The map is:

- generated;
- disposable;
- reproducible from repository artifacts;
- never a source of normative truth.

If the map disagrees with repository artifacts, rebuild the map.

## 3. Discovery sources

v1 indexes repository Markdown plus PACT metadata:

- stable IDs;
- artifact type/status;
- title;
- body text;
- canonical domain references;
- explicit aliases when present;
- explicit related IDs.

Future versions may add code symbols, routes, schemas, Git co-change, AST edges, and semantic/vector retrieval.

## 4. Ranking principles

Prefer, in order:

1. exact stable ID;
2. exact/canonical title or alias;
3. matching domain;
4. artifact text;
5. generic repository document text.

Discovery ranking affects convenience, not authority.

## 5. Owner query examples

- "之前省份和批次联动是怎么做的？"
- "工作台为什么不能自己保存批次？"
- "权限这里以前是不是改过？"
- "这个功能会影响哪些地方？"

The owner should not need file names, class names, or stable IDs.

## 6. Agent query examples

- `DOMAIN-BATCH`
- `RULE-BATCH-001`
- "batch state ownership"
- "auth public contract"

## 7. Output contract

The deterministic Discovery layer returns ranked evidence, not an invented narrative.

An AI may then produce an owner-readable explanation grounded in that evidence.

This separation prevents the search implementation from pretending it can infer product meaning.
