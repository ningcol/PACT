#!/usr/bin/env python3
"""Compare pinned legacy/current workspace reads in a disposable synthetic repository."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import statistics
import subprocess
import sys
import tempfile
import time
import types

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "pact"))
import workspace


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True).stdout


def measure(module, operation, *args):
    original = module._run_git
    count = 0

    def counted(*positional, **kwargs):
        nonlocal count
        count += 1
        return original(*positional, **kwargs)

    module._run_git = counted
    start = time.perf_counter()
    try:
        result = getattr(module, operation)(*args)
    finally:
        elapsed = time.perf_counter() - start
        module._run_git = original
    return result, {"seconds": elapsed, "git_invocations": count}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", default="6508887")
    parser.add_argument("--files", type=int, default=400)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    if not 1 <= args.files <= 10000 or not 1 <= args.repeats <= 10:
        parser.error("files must be 1..10000 and repeats 1..10")
    source = git(ROOT, "show", f"{args.baseline_ref}:scripts/pact/workspace.py")
    baseline_commit = git(ROOT, "rev-parse", args.baseline_ref).decode().strip()
    legacy = types.ModuleType("pact_legacy_workspace_benchmark")
    legacy.__file__ = str(ROOT / "scripts" / "pact" / "workspace.py")
    exec(compile(source, legacy.__file__, "exec"), legacy.__dict__)
    report = {
        "fixture": "synthetic-only; no owner project files or sessions read",
        "baseline_commit": baseline_commit,
        "baseline_workspace_sha256": hashlib.sha256(source).hexdigest(),
        "current_workspace_sha256": hashlib.sha256(pathlib.Path(workspace.__file__).read_bytes()).hexdigest(),
        "files": args.files,
        "repeats": args.repeats,
        "operations": {},
    }
    with tempfile.TemporaryDirectory(prefix="pact-workspace-batch-benchmark-") as temp:
        root = pathlib.Path(temp)
        git(root, "init", "-q")
        git(root, "config", "user.name", "PACT Synthetic Benchmark")
        git(root, "config", "user.email", "pact@example.invalid")
        for i in range(args.files):
            (root / f"source-{i:05d}.txt").write_bytes(b"base\n")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "synthetic baseline")
        for i in range(args.files // 8):
            (root / f"source-{i:05d}.txt").write_bytes(b"prepared dirty\r\n")
        prepared = legacy.task_workspace_baseline(root)
        assert workspace.task_workspace_baseline(root) == prepared
        for i in range(args.files // 8, args.files // 2):
            (root / f"source-{i:05d}.txt").write_bytes(b"task commit\n")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "synthetic intervening commit")
        for i in range(args.files // 2, args.files):
            (root / f"source-{i:05d}.txt").write_bytes(b"staged\n")
        git(root, "add", "-A")
        for i in range(args.files // 2, args.files, 2):
            (root / f"source-{i:05d}.txt").write_bytes(b"unstaged\n")
        for operation, positional in (
            ("workspace_snapshot", (root,)),
            ("task_changed_files", (root, prepared)),
        ):
            measurements = {"before": [], "after": []}
            for _ in range(args.repeats):
                before, old_time = measure(legacy, operation, *positional)
                after, new_time = measure(workspace, operation, *positional)
                if before != after:
                    raise RuntimeError(f"identity changed during {operation}")
                measurements["before"].append(old_time)
                measurements["after"].append(new_time)
            report["operations"][operation] = {
                "exact_result_equal": True,
                "runs": measurements,
                "before_median_seconds": statistics.median(x["seconds"] for x in measurements["before"]),
                "after_median_seconds": statistics.median(x["seconds"] for x in measurements["after"]),
            }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
