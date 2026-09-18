# Changes

Change artifacts describe **current change intent**, not durable project truth.

Suggested layout:

```text
docs/changes/
├── active/
└── completed/
```

Use a change artifact for work large enough that another agent may need to resume or review it.

A change artifact can include:

- goal;
- observable success;
- scope;
- constraints;
- work/progress;
- findings;
- references to durable decisions;
- verification;
- completion criteria.

Do not place durable rationale here when it belongs in a Decision Record.
