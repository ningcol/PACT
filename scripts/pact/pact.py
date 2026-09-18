#!/usr/bin/env python3
"""Stable command dispatcher for PACT runtime tools."""

from __future__ import annotations

import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent

COMMANDS = {
    "init": "init.py",
    "check": "check.py",
    "doctor": "doctor.py",
    "audit": "audit.py",
    "owner": "owner.py",
    "map": "map.py",
    "discover": "discover.py",
    "explain": "explain.py",
    "context": "context.py",
    "impact": "impact.py",
    "converge": "converge.py",
    "evidence": "evidence.py",
    "report": "report.py",
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
