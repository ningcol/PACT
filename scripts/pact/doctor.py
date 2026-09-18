#!/usr/bin/env python3
"""Inspect whether a repository has a usable PACT foundation."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[2]

REQUIRED = [
    "AGENTS.md",
    "docs/governance/constitution.md",
    "docs/governance/truth-ownership.md",
    "docs/governance/decision-authority.md",
    "docs/governance/completion-contract.md",
    "docs/governance/human-interface.md",
    "docs/product",
    "docs/architecture",
    ".agents/decisions",
    ".agents/skills",
    ".pact/schema/artifact.schema.json",
    ".pact/schema/config.schema.json",
]


def item(name: str, state: str, detail: str) -> dict:
    return {"check": name, "state": state, "detail": detail}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check PACT foundation health")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="require a project-specific .pact/config.yaml",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    checks: list[dict] = []

    for relative in REQUIRED:
        path = ROOT / relative
        checks.append(
            item(
                f"path:{relative}",
                "pass" if path.exists() else "fail",
                "present" if path.exists() else "missing",
            )
        )

    owner_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "pact" / "owner.py"),
        "--json",
    ]
    if args.strict:
        owner_cmd.append("--strict")

    owner_run = subprocess.run(owner_cmd, capture_output=True, text=True)
    if owner_run.returncode != 0:
        checks.append(
            item(
                "owner-profile",
                "fail",
                (owner_run.stdout + owner_run.stderr).strip(),
            )
        )
    else:
        try:
            owner = json.loads(owner_run.stdout)
            state = "pass" if owner.get("configured") else "warn"
            detail = (
                f"{owner.get('source')} "
                f"(language={owner.get('language')}, "
                f"technical_depth={owner.get('technical_depth')})"
            )
            checks.append(item("owner-profile", state, detail))
        except json.JSONDecodeError:
            checks.append(item("owner-profile", "fail", "owner profile output was not valid JSON"))

    check_run = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "pact" / "check.py")],
        capture_output=True,
        text=True,
    )
    checks.append(
        item(
            "deterministic-check",
            "pass" if check_run.returncode == 0 else "fail",
            (check_run.stdout + check_run.stderr).strip(),
        )
    )

    try:
        with tempfile.TemporaryDirectory(prefix="pact-doctor-") as tmp:
            output = pathlib.Path(tmp) / "project-map.json"
            map_run = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "pact" / "map.py"),
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
            )
            state = "pass" if map_run.returncode == 0 and output.exists() else "fail"
            detail = (map_run.stdout + map_run.stderr).strip()
            checks.append(item("project-map", state, detail))
    except Exception as exc:
        checks.append(item("project-map", "fail", str(exc)))

    overall = "fail" if any(c["state"] == "fail" for c in checks) else (
        "warn" if any(c["state"] == "warn" for c in checks) else "pass"
    )

    result = {"overall": overall, "checks": checks}

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"PACT doctor: {overall}")
        for check in checks:
            print(f"- [{check['state'].upper()}] {check['check']}: {check['detail']}")

    return 1 if overall == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
