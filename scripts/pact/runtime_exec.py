"""Locate and invoke the active PACT runtime from source or an adopted project."""

from __future__ import annotations

import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[2]


def runtime_entry(root: pathlib.Path = ROOT) -> pathlib.Path:
    compact = root / ".pact" / "pact.pyz"
    if compact.is_file():
        return compact

    source = root / "scripts" / "pact" / "pact.py"
    if source.is_file():
        return source

    raise FileNotFoundError(
        f"PACT runtime not found under {root}: expected {compact} or {source}"
    )


def runtime_command(
    command: str,
    *args: str,
    root: pathlib.Path = ROOT,
) -> list[str]:
    return [
        sys.executable,
        str(runtime_entry(root)),
        command,
        *[str(arg) for arg in args],
    ]
