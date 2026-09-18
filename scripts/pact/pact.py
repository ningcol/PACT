#!/usr/bin/env python3
"""Stable command dispatcher for PACT runtime tools."""

from __future__ import annotations

import pathlib
import subprocess
import sys

if sys.version_info < (3, 11):
    print("PACT 0.3 requires Python 3.11+.", file=sys.stderr)
    raise SystemExit(2)

HERE = pathlib.Path(__file__).resolve().parent

COMMANDS = {
    "init": "init.py",
    "upgrade": "upgrade.py",
    "version": "version.py",
    "check": "check.py",
    "doctor": "doctor.py",
    "readiness": "readiness.py",
    "audit": "audit.py",
    "owner": "owner.py",
    "fitness": "fitness.py",
    "map": "map.py",
    "code-map": "code_map.py",
    "discover": "discover.py",
    "explain": "explain.py",
    "context": "context.py",
    "impact": "impact.py",
    "converge": "converge.py",
    "evidence": "evidence.py",
    "report": "report.py",
    "eval": "eval.py",
}


def help_text() -> str:
    commands = "\n".join(f"  {name}" for name in COMMANDS)
    return f"""PACT Project AI Control Plane

Usage:
  python scripts/pact/pact.py <command> [args...]

Commands:
{commands}

PACT keeps this dispatcher stable while individual implementations remain replaceable.
"""


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help", "help"}:
        print(help_text())
        return 0

    command = sys.argv[1]
    script = COMMANDS.get(command)
    if not script:
        print(f"Unknown PACT command: {command}", file=sys.stderr)
        print(help_text(), file=sys.stderr)
        return 2

    completed = subprocess.run(
        [sys.executable, str(HERE / script), *sys.argv[2:]]
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
