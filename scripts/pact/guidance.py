"""Version-matched, read-only agent guidance distributed with the runtime."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

# Direct execution is also read-only. The dispatcher sets this before importing
# this module; here it must precede importing any project-local dependency.
if __name__ == "__main__":
    sys.dont_write_bytecode = True

from runtime_identity import runtime_identity


ROOT = pathlib.Path(__file__).resolve().parents[2]

STANDARD_GUIDANCE = """# PACT Standard Agent Guidance

Read once per session using PACT, and after runtime upgrades, not at every task
or finish. Use the project's approved interpreter; example `python3` commands
do not authorize another environment or project checks.

Preserve existing project rules, stricter permissions and authoritative knowledge
locations. The routes below are defaults; do not relocate or duplicate knowledge.

## Core rules

1. Preserve confirmed Product Truth.
2. Acquire sufficient context before changing behavior; do not read everything by default.
3. AI owns implementation decisions unless they change product meaning, permissions/policy, irreversible outcomes, material risk, or cost.
4. Distinguish normative truth (what should happen) from descriptive truth (what currently happens).
5. Verify observable outcomes before claiming completion.
6. Reconcile drift by authority; never make Product Truth follow code automatically.
7. Report owner-facing results in product/business language by default.

## Knowledge router

- Governance extensions: `docs/governance/`
- Product Truth and vocabulary: `docs/product/`
- Current architecture: `docs/architecture/`
- Durable engineering rationale: `.agents/decisions/`
- Active/completed change intent: `docs/changes/`
- Drift: `docs/drift/`
- Reusable procedures: `.agents/skills/`
- Adoption readiness: `.pact/baseline.toml`

Create a location only for real durable knowledge, not empty folders/templates.
Absent optional directories are not failures. Init does not certify knowledge.
Treat pending baseline reviews as incomplete/unknown; never infer missing truth
or product approval from code or tests.

## Proportionate task workflow

Use project procedures for explanations, investigations and small changes.
PACT's Task/Change workflow is optional; a prepared Contract's acceptance/Evidence
gates remain binding. Use lower-level primitives without weakening those gates.

For work needing a prepared task:

1. Use `python3 pact.py status` / `inspect` when project state or history is unclear.
2. Prepare with `python3 pact.py task prepare "<task>" --success "<observable outcome>" --risk <level>`.
3. Implement ordinary technical details autonomously within the Task Contract and Context.
4. Verify through `python3 pact.py task verify <TASK-ID> --criterion AC-1 --claim "<specific check>" -- <command>` or lower-level `run` where practical.
5. Provide Evidence, Convergence and Owner Report. Optional `task draft <TASK-ID>` creates incomplete drafts; `task assist <TASK-ID> --json` is read-only; `task assist <TASK-ID> --write-draft` fills empty machine fields from trusted Evidence and keeps the report `partial`. Review existing fields manually, then acceptance/Convergence before marking it completed. Valid manually reviewed bundles may finish directly.
6. Convergence binds the prepared Context, explicitly reviews every selected knowledge artifact, and gives `change_coverage` rationale for each path differing from preparation. Empty findings do not replace coverage. In drafts, resolve `knowledge_retention` pending to `none`, `update`, `create` or `update-and-create`, with reason and changed knowledge paths. Routine fixes usually need no Rule/Decision; code changes alone never justify one.
7. Finish with `python3 pact.py task finish <TASK-ID>`. Every acceptance criterion must be verified and owner-visible, relevant knowledge converged and blocking ambiguity resolved. Use `--require-knowledge-retention` when explicitly required. Tests alone do not establish completion; do not claim PACT-verified completion if this gate fails.

Recover paths with `python3 pact.py task status <TASK-ID> --json`. Preparation
includes existing dirty content in its baseline; unchanged pre-existing content
is excluded from its delta. Other writes in a shared checkout may enter it;
PACT does not identify authors. Continue with status/resume. `prepare --force`
starts a new baseline including current edits and archives old state without
automatically carrying Evidence forward. Current bindings/provenance still need
verification; force does not revoke every old receipt.

## Ownership and decision boundaries

Ordinary business tasks must not patch framework-managed launchers, runtime,
embedded schemas or standard instructions. Use the supported upgrade procedure
within an authorized PACT maintenance task; report generic defects upstream with
reproductions. Upstream PACT source remains editable under normal review.

Project config, rules, business docs, skills and custom checks retain project
authority. Generated task state, receipts and install bookkeeping are tool-maintained;
never forge hashes, results or ownership to manufacture completion. Writable state
is not a customization surface.

Keep necessary differences in existing guides/config; full copies shadow updates.
Upgrades preserve project instructions: reconcile old copies and read current
runtime guidance. Resolve conflicts by authority without weakening confirmed
truth, permissions or Evidence. Capability support proves neither enablement
nor executed checks.

Do not ask the owner to choose ordinary implementation mechanisms. Escalate only
changes to user-observable behavior, business/data meaning, permissions/policy,
irreversible outcomes, or material risk/cost.

An Owner may explicitly accept limited delivery with unverified work. Disclose
acceptance and remaining gaps in the existing project Change/owner-facing result;
leave `task finish` success and `complete=true` unsatisfied. Do not relabel missing
or failed checks as passed, waive security/legal/deployment requirements, or
silently change a Task Contract.

## Communication and verification limits

Before owner-facing output, read `python3 pact.py owner --json`. Honor the validated
Owner Profile's language, technical depth, consequence-first translation and
progressive-disclosure preferences.

This command outputs guidance only. File existence, hashes and local manifest
matches do not prove host loading, agent compliance, trusted release origin or
OS write protection. Markdown links are not universal native imports. Verify
actual host loading and edit/Shell/plugin protection separately; do not label
an untested integration as loaded or locked.
"""


PROJECT_ENTRY = """# Project Agent Guide

This project uses PACT (Project AI Control Plane).

At the start of a session using PACT, read the standard guidance from the
current runtime with the project's approved Python interpreter:

```bash
python3 pact.py guidance
```

`python3` is a placeholder for that interpreter. Read again after a runtime
upgrade, not on every task or finish. Keep project-specific rules, knowledge
routes and verification commands in their existing authoritative locations;
follow their permissions and decision boundaries. Do not copy the full
standard guidance here or patch framework-managed files in ordinary tasks.

This entry is project-owned. Its presence does not verify host loading,
agent compliance or OS write protection.
"""


def minimal_project_entry() -> str:
    """Stable project-owned entry; standard content stays in the runtime."""
    return PROJECT_ENTRY


def entry_reference_present(contents: str) -> bool:
    """Recognize a bounded command reference, never infer actual host loading."""
    return re.search(
        r"(?<![\w.-])(?:\./)?pact\.py[ \t]+guidance(?=$|[\s`'\";|&])",
        contents,
        re.MULTILINE,
    ) is not None


def bootstrap_snippet() -> str:
    """Offer a short integration instruction without copying standard rules."""
    return (
        "# PACT Agent Bootstrap\n\n"
        "An existing `AGENTS.md` was detected, so PACT did not overwrite it.\n"
        "Integrate the short entry below into that guide, or its existing PACT\n"
        "router. Keep project rules and authorized knowledge locations intact.\n"
        "Do not copy the full standard guidance. Remove this bootstrap after\n"
        "integration; its existence alone does not establish host loading.\n\n"
        + PROJECT_ENTRY
    )


def guidance_info(root: pathlib.Path | None = None, *, include_content: bool = True) -> dict:
    """Describe supplied guidance, without inspecting project behavior/state."""
    source_kind = "embedded-runtime" if getattr(__loader__, "archive", None) else "source"
    result = {
        "format_version": 1,
        "content_sha256": hashlib.sha256(STANDARD_GUIDANCE.encode("utf-8")).hexdigest(),
        "source": {"kind": source_kind, "path": "guidance.py"},
        "runtime": runtime_identity(ROOT if root is None else root),
        "verification": {
            "host_loading": "unverified",
            "behavioral_compliance": "unverified",
            "write_protection": "unverified",
        },
    }
    if include_content:
        result["content"] = STANDARD_GUIDANCE
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read standard agent guidance from the current PACT runtime (no project checks or writes)"
    )
    parser.add_argument("--json", action="store_true", help="include content hash and runtime identity")
    args = parser.parse_args()
    if args.json:
        print(json.dumps(guidance_info(), ensure_ascii=True, indent=2))
    else:
        info = guidance_info(include_content=False)
        identity = info["runtime"]
        integrity = identity.get("integrity", "unknown")
        print(
            f"PACT standard guidance: runtime={identity['version']} "
            f"integrity={integrity} source={info['source']['kind']} "
            f"content_sha256={info['content_sha256']}"
        )
        if integrity not in {"matched", "source"}:
            print(f"Warning: runtime identity is {integrity}; this guidance read does not validate the install.")
        for error in identity.get("errors", []):
            print(f"- runtime identity error: {error}")
        print("Output only; host loading, compliance and write protection remain unverified.\n")
        print(STANDARD_GUIDANCE, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
