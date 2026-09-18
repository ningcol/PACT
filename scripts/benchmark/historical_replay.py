#!/usr/bin/env python3
"""Replay real historical tasks to measure PACT Context retrieval.

This benchmark does not run a coding Agent and does not judge implementation
quality. It checks whether pre-change Context retrieval includes source files
that were actually changed by the later historical commit.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import subprocess
import sys
import tempfile


PACT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_CASES = PACT_ROOT / "benchmarks" / "brownfield" / "cases.json"


def run(
    command: list[str],
    *,
    cwd: pathlib.Path | None = None,
    timeout: int = 300,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result


def load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def clone_at(repository: str, base_commit: str, target: pathlib.Path) -> None:
    url = f"https://github.com/{repository}.git"
    run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout", url, str(target)])
    checkout = subprocess.run(
        ["git", "checkout", "--quiet", base_commit],
        cwd=target,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if checkout.returncode == 0:
        return

    run(["git", "fetch", "--quiet", "origin", base_commit], cwd=target, timeout=180)
    run(["git", "checkout", "--quiet", base_commit], cwd=target)


def prepare_direct(target: pathlib.Path, case: dict) -> dict:
    task_id = f"BENCH-{case['id'].upper().replace('_', '-').replace(' ', '-')}"
    result = run(
        [
            sys.executable,
            str(target / "pact.py"),
            "task",
            "prepare",
            case["task"],
            "--success",
            case["success"],
            "--risk",
            case.get("risk_level", "medium"),
            "--code",
            "--task-id",
            task_id,
            "--json",
        ],
        cwd=target,
    )
    return json.loads(result.stdout)


def expanded_context(target: pathlib.Path, case: dict, output: pathlib.Path) -> dict:
    run(
        [
            sys.executable,
            str(target / "pact.py"),
            "context",
            case["task"],
            "--success",
            case["success"],
            "--risk",
            case.get("risk_level", "medium"),
            "--code",
            "--query",
            case["expanded_query"],
            "--output",
            str(output),
        ],
        cwd=target,
    )
    return load_json(output)


def context_metrics(context: dict, oracle_files: list[str]) -> dict:
    paths = [item["path"] for item in context.get("code_artifacts", [])]
    path_set = set(paths)
    matched = [path for path in oracle_files if path in path_set]
    ranks = {
        path: paths.index(path) + 1
        for path in matched
    }

    recall = len(matched) / len(oracle_files) if oracle_files else None
    precision_proxy = len(matched) / len(paths) if paths else 0.0

    return {
        "context_code_files": len(paths),
        "oracle_files": len(oracle_files),
        "matched_oracle_files": matched,
        "missing_oracle_files": [
            path for path in oracle_files if path not in path_set
        ],
        "oracle_ranks": ranks,
        "recall": recall,
        "precision_proxy": precision_proxy,
        "known_unknowns": len(context.get("known_unknowns", [])),
    }


def replay_case(case: dict) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"pact-bench-{case['id']}-") as tmp:
        target = pathlib.Path(tmp) / "target"
        clone_at(case["repository"], case["base_commit"], target)

        run(
            [
                sys.executable,
                str(PACT_ROOT / "scripts" / "pact" / "init.py"),
                "--target",
                str(target),
                "--apply",
            ],
            cwd=PACT_ROOT,
        )

        available_oracle = [
            path
            for path in case["oracle_files"]
            if (target / path).is_file()
        ]
        missing_at_base = [
            path
            for path in case["oracle_files"]
            if not (target / path).is_file()
        ]

        prepared = prepare_direct(target, case)
        direct = load_json(target / prepared["context"])

        expanded_path = target / ".pact" / "tasks" / prepared["task_id"] / "expanded-context.json"
        expanded = expanded_context(target, case, expanded_path)

        direct_metrics = context_metrics(direct, available_oracle)
        expanded_metrics = context_metrics(expanded, available_oracle)

        return {
            "id": case["id"],
            "repository": case["repository"],
            "base_commit": case["base_commit"],
            "target_commit": case["target_commit"],
            "task": case["task"],
            "expanded_query": case["expanded_query"],
            "oracle_missing_at_base": missing_at_base,
            "direct": direct_metrics,
            "expanded": expanded_metrics,
            "query_expansion_recall_delta": (
                (expanded_metrics["recall"] or 0.0)
                - (direct_metrics["recall"] or 0.0)
            ),
        }


def aggregate(results: list[dict]) -> dict:
    oracle_total = sum(item["direct"]["oracle_files"] for item in results)
    direct_hits = sum(
        len(item["direct"]["matched_oracle_files"]) for item in results
    )
    expanded_hits = sum(
        len(item["expanded"]["matched_oracle_files"]) for item in results
    )

    return {
        "case_count": len(results),
        "oracle_file_count": oracle_total,
        "direct_weighted_recall": (
            direct_hits / oracle_total if oracle_total else None
        ),
        "expanded_weighted_recall": (
            expanded_hits / oracle_total if oracle_total else None
        ),
        "cases_improved_by_query_expansion": sum(
            item["query_expansion_recall_delta"] > 0
            for item in results
        ),
        "mean_direct_context_code_files": (
            statistics.fmean(
                item["direct"]["context_code_files"] for item in results
            )
            if results
            else None
        ),
        "mean_expanded_context_code_files": (
            statistics.fmean(
                item["expanded"]["context_code_files"] for item in results
            )
            if results
            else None
        ),
        "interpretation": (
            "Historical retrieval benchmark only. Oracle files are source files "
            "actually changed by the later commit. precision_proxy is not semantic "
            "precision because extra Context files may still be relevant. Low recall "
            "is evidence for retrieval improvement, not a benchmark harness failure."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="PACT historical brownfield retrieval benchmark")
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--output")
    args = parser.parse_args()

    config = load_json(pathlib.Path(args.cases))
    cases = config.get("cases", [])
    if args.case_ids:
        wanted = set(args.case_ids)
        cases = [case for case in cases if case.get("id") in wanted]
        missing = sorted(wanted - {case.get("id") for case in cases})
        if missing:
            print(f"Unknown benchmark case(s): {', '.join(missing)}", file=sys.stderr)
            return 2

    results = []
    failures = []
    for case in cases:
        try:
            result = replay_case(case)
            results.append(result)
            print(
                f"{case['id']}: direct recall={result['direct']['recall']:.3f} "
                f"expanded recall={result['expanded']['recall']:.3f}"
            )
        except Exception as exc:
            failures.append({"id": case.get("id"), "error": str(exc)})
            print(f"{case.get('id')}: HARNESS ERROR: {exc}", file=sys.stderr)

    report = {
        "version": 1,
        "results": results,
        "summary": aggregate(results),
        "harness_failures": failures,
    }

    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = pathlib.Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
