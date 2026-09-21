#!/usr/bin/env python3
"""Inspect whether a repository has a usable PACT foundation."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

from distribution import read_install_manifest, resolve_install_target, sha256_file
from runtime_exec import runtime_command


ROOT = pathlib.Path(__file__).resolve().parents[2]

SOURCE_REQUIRED = [
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
    ".pact/VERSION",
    "LICENSE",
]

# Adopted projects may use the minimal profile. Optional knowledge locations are
# absent until the project has durable knowledge to place there.
ADOPTED_REQUIRED = [
    "AGENTS.md",
    "pact.py",
    ".pact/pact.pyz",
    ".pact/VERSION",
    ".pact/LICENSE",
]


def item(name: str, state: str, detail: str) -> dict:
    return {"check": name, "state": state, "detail": detail}


def install_provenance_check(strict: bool) -> dict:
    try:
        manifest = read_install_manifest(ROOT)
    except ValueError as exc:
        return item(
            "install-provenance",
            "fail",
            f"cannot validate install manifest: {exc}",
        )

    if manifest is None:
        return item(
            "install-provenance",
            "fail" if strict else "warn",
            "missing .pact/install.json"
            if strict
            else "source/untracked checkout; no install manifest",
        )

    try:
        version_path = resolve_install_target(ROOT, ".pact/VERSION")
        if not version_path.is_file():
            return item(
                "install-provenance",
                "fail",
                "missing framework file: .pact/VERSION",
            )
        installed_version = version_path.read_text(encoding="utf-8").strip()
        manifest_version = manifest["runtime_version"]
        if installed_version != manifest_version:
            return item(
                "install-provenance",
                "fail",
                f"VERSION={installed_version!r} but install manifest "
                f"runtime_version={manifest_version!r}",
            )

        integrity_errors = []
        for relative, record in manifest["files"].items():
            if record.get("management") != "framework":
                continue
            try:
                path = resolve_install_target(ROOT, relative)
            except ValueError as exc:
                integrity_errors.append(str(exc))
                continue
            if not path.is_file():
                integrity_errors.append(f"missing framework file: {relative}")
                continue
            actual_sha = sha256_file(path)
            expected_sha = record.get("installed_sha256")
            if actual_sha != expected_sha:
                integrity_errors.append(
                    f"framework file modified/corrupt: {relative} "
                    f"({actual_sha} != {expected_sha})"
                )

        if integrity_errors:
            return item(
                "install-provenance",
                "fail" if strict else "warn",
                "; ".join(integrity_errors[:10]),
            )

        return item(
            "install-provenance",
            "pass",
            f"runtime={manifest_version}, tracked_files={len(manifest['files'])}",
        )
    except (OSError, ValueError) as exc:
        return item(
            "install-provenance",
            "fail",
            f"cannot validate install manifest: {exc}",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check PACT foundation health")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="require project config and tracked install provenance",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    checks: list[dict] = []

    adopted = (ROOT / ".pact" / "install.json").is_file()
    required_paths = ADOPTED_REQUIRED if adopted else SOURCE_REQUIRED

    for relative in required_paths:
        path = ROOT / relative
        checks.append(
            item(
                f"path:{relative}",
                "pass" if path.exists() else "fail",
                "present" if path.exists() else "missing",
            )
        )

    owner_cmd = runtime_command("owner", "--json")
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

    checks.append(install_provenance_check(args.strict))

    fitness_cmd = runtime_command("fitness", "--json", "--validate-only")
    if args.strict:
        fitness_cmd.append("--strict")

    fitness_run = subprocess.run(fitness_cmd, capture_output=True, text=True)
    if fitness_run.returncode != 0:
        checks.append(
            item(
                "architecture-fitness",
                "fail",
                (fitness_run.stdout + fitness_run.stderr).strip(),
            )
        )
    else:
        try:
            fitness = json.loads(fitness_run.stdout)
            state = "pass" if fitness.get("configured") else "warn"
            detail = (
                f"{fitness.get('config_source')} "
                f"(checks={fitness.get('check_count')})"
            )
            checks.append(item("architecture-fitness", state, detail))
        except json.JSONDecodeError:
            checks.append(
                item(
                    "architecture-fitness",
                    "fail",
                    "fitness validation output was not valid JSON",
                )
            )

    check_run = subprocess.run(
        runtime_command("check"),
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

    project_map = ROOT / ".pact" / "cache" / "project-map.json"
    try:
        map_run = subprocess.run(
            runtime_command(
                "map",
                "--output",
                str(project_map),
                "--ensure",
            ),
            capture_output=True,
            text=True,
        )
        state = (
            "pass"
            if map_run.returncode == 0 and project_map.is_file()
            else "fail"
        )
        detail = (map_run.stdout + map_run.stderr).strip()
        checks.append(item("project-map", state, detail))
    except Exception as exc:
        checks.append(item("project-map", "fail", str(exc)))

    overall = "fail" if any(c["state"] == "fail" for c in checks) else (
        "warn" if any(c["state"] == "warn" for c in checks) else "pass"
    )

    result = {
        "overall": overall,
        "checks": checks,
        "project_map": (
            project_map.relative_to(ROOT).as_posix()
            if project_map.is_file()
            else None
        ),
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"PACT doctor: {overall}")
        for check in checks:
            print(f"- [{check['state'].upper()}] {check['check']}: {check['detail']}")

    return 1 if overall == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
