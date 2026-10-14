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

A matching source fingerprint is necessary but not sufficient to reuse a cache. PACT verifies expected document paths and essential record fields before considering the Project Map fresh. A structurally corrupted index is rebuilt using repository Markdown as the input. Index and per-file cache files are atomically replaced one by one; no joint multi-cache transaction or tamper-proof guarantee is implied.

Source enumeration is shared with deterministic Markdown checks: in Git
repositories, tracked and non-ignored untracked files are candidates, while
project-specific transient files belong in `.gitignore`. Do not globally
exclude names such as `tmp*` that could hide tracked project truth. A vanished
or changing source triggers a bounded whole-scan retry; after three unstable
attempts the operation fails without publishing a new Project Map. The
input-list/content fingerprint is checked again before publication. This is
best-effort consistency under noncooperating writers, **not** an atomic
filesystem snapshot or a lock across all source files.

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

## 4. Multi-query retrieval

Owner language, business vocabulary, and code vocabulary often differ.

PACT accepts multiple independent discovery queries and fuses their ranked results with deterministic Reciprocal Rank Fusion (RRF). This avoids concatenating unrelated terms into one large lexical query where every extra term can distort ranking.

Multi-query retrieval has two important boundaries:

- each query is a search hypothesis, not authority;
- the final fused result is capped by the normal knowledge/code budget.

Single-query behavior remains backward compatible. Multi-query mode adds cross-query evidence and deduplicates results before the final budget is applied.

Typical Agent expansion:

```text
owner phrase
    +
canonical alias
    +
code/symbol phrase
    +
state/contract phrase
        ↓
independent lexical + graph retrieval
        ↓
RRF fusion
        ↓
final Context budget
```

PACT does not call an LLM to invent queries. The calling Agent may generate the query set using the conversation and project vocabulary it already has.

## 5. Ranking principles

Prefer, in order:

1. exact stable ID;
2. exact/canonical title or alias;
3. matching domain;
4. artifact text;
5. generic repository document text.

Discovery ranking affects convenience, not authority.

For generic queries, decisions marked `archived` or `superseded` receive a
soft relevance penalty. They remain searchable (including exact ID, title and
alias lookup), and results retain their lifecycle status. A rejected alternative
is not automatically historical: its rationale may still matter. This ranking
preference **does not** turn the remaining search results into authoritative
current truth; an Agent must reconcile status and project authority.

## 6. Owner query examples

- "之前省份和批次联动是怎么做的？"
- "工作台为什么不能自己保存批次？"
- "权限这里以前是不是改过？"
- "这个功能会影响哪些地方？"

The owner should not need file names, class names, or stable IDs.

## 7. Agent query examples

- `DOMAIN-BATCH`
- `RULE-BATCH-001`
- "batch state ownership"
- "auth public contract"

## 8. Output contract

The deterministic Discovery layer returns ranked evidence, not an invented narrative.

An AI may then produce an owner-readable explanation grounded in that evidence.

This separation prevents the search implementation from pretending it can infer product meaning.
