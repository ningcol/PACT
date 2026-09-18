#!/usr/bin/env python3
"""Run project-owned PACT architecture fitness functions."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

import yaml
from jsonschema import Draft202012Validator


def load_yaml(path: pathlib.Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("fitness configuration root must be an object")
    return data


def validate(config: dict, schema_path: pathlib.Path) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(config), key=lambda e: list(e.path)):
        loc = ".".join(str(p) for p in err.path)
        errors.append(f"{loc or '<root>'}: {err.message}")
    return errors


def run_check(root: pathlib.Path, check: dict) -> dict:
    timeout = int(check.get("timeout_seconds", 120))
    enabled = check.get("enabled", True)

    if not enabled:
        return {
            "id": check["id"],
            "description": check["description"],
            "severity": check["severity"],
            "status": "skipped",
            "exit_code": None,
            "stdout": "",
            "stderr": "",
        }

    try:
        completed = subprocess.run(
            check["command"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        status = "pass" if completed.returncode == 0 else "fail"
        return {
            "id": check["id"],
            "description": check["description"],
            "severity": check["severity"],
            "status": status,
            "exit_code": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "id": check["id"],
            "description": check["description"],
            "severity": check["severity"],
            "status": "fail",
            "exit_code": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": f"timed out after {timeout}s",
        }
    except OSError as exc:
        return {
            "id": check["id"],
            "description": check["description"],
            "severity": check["severity"],
            "status": "fail",
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PACT architecture fitness functions")
    parser.add_argument("--root", help="repository root; defaults to this script's repository")
    parser.add_argument("--config", help="fitness config path; defaults to .pact/fitness.yaml")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="require project .pact/fitness.yaml instead of falling back to the example",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="validate configuration without executing project checks",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    default_root = pathlib.Path(__file__).resolve().parents[2]
    root = pathlib.Path(args.root).expanduser().resolve() if args.root else default_root

    if args.config:
        config_path = pathlib.Path(args.config)
        if not config_path.is_absolute():
            config_path = root / config_path
        configured = config_path.name == "fitness.yaml"
    else:
        project_config = root / ".pact" / "fitness.yaml"
        example_config = root / ".pact" / "fitness.example.yaml"
        if project_config.exists():
            config_path = project_config
            configured = True
        elif not args.strict and example_config.exists():
            config_path = example_config
            configured = False
        else:
            config_path = project_config
            configured = False

    schema_path = root / ".pact" / "schema" / "fitness.schema.json"

    if not schema_path.exists():
        print(f"PACT fitness: missing schema at {schema_path}", file=sys.stderr)
        return 2
    if not config_path.exists():
        print(f"PACT fitness: missing config at {config_path}", file=sys.stderr)
        return 2

    try:
        config = load_yaml(config_path)
    except Exception as exc:
        print(f"PACT fitness: cannot parse config: {exc}", file=sys.stderr)
        return 2

    errors = validate(config, schema_path)
    if errors:
        print("PACT fitness: invalid config", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    if args.validate_only:
        summary = {
            "overall": "pass",
            "configured": configured,
            "config_source": config_path.relative_to(root).as_posix() if config_path.is_relative_to(root) else str(config_path),
            "check_count": len(config["checks"]),
            "blocking_failures": 0,
            "warnings": 0,
            "validated_only": True,
            "results": [],
        }
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print("PACT fitness: config valid")
            print(f"- source: {summary['config_source']}")
            print(f"- configured checks: {summary['check_count']}")
        return 0

    results = [run_check(root, check) for check in config["checks"]]

    blocking = [
        item
        for item in results
        if item["status"] == "fail" and item["severity"] == "error"
    ]
    warnings = [
        item
        for item in results
        if item["status"] == "fail" and item["severity"] == "warn"
    ]

    summary = {
        "overall": "fail" if blocking else ("warn" if warnings else "pass"),
        "configured": configured,
        "config_source": config_path.relative_to(root).as_posix() if config_path.is_relative_to(root) else str(config_path),
        "check_count": len(results),
        "blocking_failures": len(blocking),
        "warnings": len(warnings),
        "validated_only": False,
        "results": results,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"PACT fitness: {summary['overall']}")
        if not configured:
            print(f"Using example fitness config: {summary['config_source']}")
        if not results:
            print("No architecture fitness functions configured.")
        for item in results:
            print(
                f"- [{item['status'].upper()}] {item['id']} "
                f"({item['severity']}): {item['description']}"
            )
            if item["status"] == "fail":
                if item["stdout"]:
                    print(f"  stdout: {item['stdout']}")
                if item["stderr"]:
                    print(f"  stderr: {item['stderr']}")

    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
