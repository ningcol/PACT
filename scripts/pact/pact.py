#!/usr/bin/env python3
"""Stable command dispatcher for PACT runtime tools."""

from __future__ import annotations

import importlib
import pathlib
import sys

if sys.version_info < (3, 11):
    print("PACT 0.3 requires Python 3.11+.", file=sys.stderr)
    raise SystemExit(2)

RUNTIME_ROOT = pathlib.Path(__file__).resolve().parent
runtime_path = str(RUNTIME_ROOT)
if runtime_path not in sys.path:
    sys.path.insert(0, runtime_path)

COMMANDS = {
    # Recommended agent-facing surface.
    "status": "status",
    "inspect": "inspect_project",
    "task": "task",

    # Setup / maintenance.
    "init": "init",
    "upgrade": "upgrade",
    "version": "version",

    # Advanced primitives.
    "check": "check",
    "schema-lint": "schema_lint",
    "workflow-lint": "workflow_lint",
    "doctor": "doctor",
    "readiness": "readiness",
    "audit": "audit",
    "owner": "owner",
    "risk": "risk",
    "fitness": "fitness",
    "map": "map",
    "code-map": "code_map",
    "discover": "discover",
    "explain": "explain",
    "context": "context",
    "impact": "impact",
    "run": "run",
    "converge": "converge",
    "evidence": "evidence",
    "report": "report",
    "complete": "complete",
    "eval": "eval",
}

RECOMMENDED = [
    ("status", "project foundation/readiness/health summary"),
    ("inspect", "inspect a remembered feature/business behavior"),
    ("task prepare", "prepare risk-adaptive context for a task"),
    ("task finish", "validate an existing completion bundle"),
    ("task status", "show one prepared task"),
]

SETUP = [
    ("init", "safely adopt PACT"),
    ("upgrade", "transactionally upgrade PACT runtime"),
    ("version", "show runtime/install version"),
]


def help_text() -> str:
    recommended = "\n".join(f"  {name:<14} {desc}" for name, desc in RECOMMENDED)
    setup = "\n".join(f"  {name:<14} {desc}" for name, desc in SETUP)
    advanced_names = [
        name
        for name in COMMANDS
        if name not in {"status", "inspect", "task", "init", "upgrade", "version"}
    ]
    advanced = "  " + "  ".join(advanced_names)

    return f"""PACT Project AI Control Plane

Usage:
  python3 pact.py <command> [args...]

Recommended agent surface:
{recommended}

Setup / maintenance:
{setup}

Advanced primitives:
{advanced}

Use low-level primitives when the default task surface is insufficient.
PACT keeps the primitives stable so stronger agents can bypass unnecessary
orchestration without weakening truth/evidence requirements.
"""


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help", "help"}:
        print(help_text())
        return 0

    command = sys.argv[1]
    module_name = COMMANDS.get(command)
    if not module_name:
        print(f"Unknown PACT command: {command}", file=sys.stderr)
        print(help_text(), file=sys.stderr)
        return 2

    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        print(f"PACT command load failed ({command}): {exc}", file=sys.stderr)
        return 2

    child_main = getattr(module, "main", None)
    if not callable(child_main):
        print(
            f"PACT command module has no callable main(): {module_name}",
            file=sys.stderr,
        )
        return 2

    previous_argv = sys.argv
    try:
        sys.argv = [command, *previous_argv[2:]]
        return int(child_main())
    finally:
        sys.argv = previous_argv


if __name__ == "__main__":
    raise SystemExit(main())
