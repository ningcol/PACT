#!/usr/bin/env python3
"""PACT-only synthetic retrieval regression; not a blinded real-Agent pilot.

Never fetch or modify any external repository. Only writes to a temporary
directory, installing PACT directly from this source checkout. An oracle is
loaded only after both Context results are frozen on disk.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import tempfile
import time


ROOT = pathlib.Path(__file__).resolve().parents[2]
CASES = ROOT / "benchmarks" / "brownfield" / "eight-stage-synthetic-inputs.json"
ORACLE = ROOT / "benchmarks" / "brownfield" / "eight-stage-synthetic-oracle.json"


def run(command: list[str], *, cwd: pathlib.Path, timeout: int = 120) -> None:
    result = subprocess.run(
        command, cwd=cwd, capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"PACT-only fixture command failed: {command[1:3]!r}: "
            f"{result.returncode}\n{result.stderr[:2000]}"
        )


def _safe_file(root: pathlib.Path, relative: str) -> pathlib.Path:
    raw = pathlib.PurePosixPath(relative)
    if not relative or raw.is_absolute() or ".." in raw.parts or "\\" in relative:
        raise ValueError("unsafe synthetic fixture relative path")
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("synthetic fixture escaped sandbox")
    return resolved


def _install(target: pathlib.Path, case: dict) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for item in case["files"]:
        path = _safe_file(target, item["path"])
        if not item["path"].startswith("src/"):
            raise ValueError("synthetic case may only supply src/ fixture files")
        if len(item["text"]) > 20000:
            raise ValueError("synthetic file text exceeds size cap")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(item["text"], encoding="utf-8")
    run(
        [sys.executable, str(ROOT / "scripts" / "pact" / "init.py"),
         "--target", str(target), "--apply"],
        cwd=ROOT,
    )
    if not (target / "pact.py").is_file():
        raise RuntimeError("isolated PACT installation was incomplete")


def _context(target: pathlib.Path, case: dict, mode: str) -> dict:
    output = target / ".pact" / "tmp" / f"bench-{mode}.json"
    command = [
        sys.executable, str(target / "pact.py"), "context",
        case["task"], "--success", case["success"],
        "--risk", case["risk_level"], "--code",
        "--code-limit", str(case["code_limit"]),
        "--token-budget", str(case["token_budget"]),
        "--output", str(output),
    ]
    if mode != "default":
        command.extend(["--intent", mode])
    start = time.perf_counter()
    run(command, cwd=target)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
    envelope = json.loads(output.read_text(encoding="utf-8"))
    paths = [item["path"] for item in envelope.get("code_artifacts", [])]
    if len(paths) > case["code_limit"]:
        raise RuntimeError("synthetic Context exceeds frozen code limit")
    metrics = {
        "mode": mode,
        "paths": paths,
        "code_file_count": len(paths),
        "known_unknown_count": len(envelope.get("known_unknowns", [])),
        "selected_estimated_tokens":
            envelope.get("context_budget", {}).get("selected_estimated_tokens"),
        "elapsed_ms": elapsed_ms,
    }
    return metrics


def score(metric: dict, oracle: list[str]) -> dict:
    """Return a retrieval proxy, not semantic correctness or Owner benefit."""
    hits = [path for path in oracle if path in metric["paths"]]
    return {
        **metric,
        "oracle_count": len(oracle),
        "matched_oracle_files": hits,
        "missing_oracle_files": [path for path in oracle if path not in metric["paths"]],
        "recall": len(hits) / len(oracle) if oracle else None,
        "precision_proxy":
            len(hits) / metric["code_file_count"] if metric["code_file_count"] else 0.0,
    }


def evaluate_case(case: dict, expected: list[str], *, parent: pathlib.Path) -> dict:
    target = parent / case["id"]
    _install(target, case)
    # Do NOT copy the oracle into the fixture or pass it as a query.
    assert not (target / ORACLE.name).exists()
    default = _context(target, case, "default")
    work = _context(target, case, "work")
    return {
        "id": case["id"],
        "task": case["task"],
        "risk": case["risk_level"],
        "code_limit": case["code_limit"],
        "token_budget": case["token_budget"],
        "source": "PACT-owned synthetic isolated installed runtime",
        "default": score(default, expected),
        "work": score(work, expected),
        "oracle_is_synthetic": True,
        "real_agent_executed": False,
        "owner_data_observed": False,
    }


def evaluate(inputs: dict, oracle: dict) -> dict:
    cases = inputs["cases"]
    expected_by_id = oracle["cases"]
    ids = [item["id"] for item in cases]
    if (len(ids) != len(set(ids)) or not ids
            or set(ids) != set(expected_by_id)):
        raise ValueError("inputs and synthetic oracle do not match exactly")
    results = []
    with tempfile.TemporaryDirectory(prefix="pact-eight-stage-synthetic-") as tmp:
        root = pathlib.Path(tmp)
        for case in cases:
            # Oracle value is not consulted during context generation.
            results.append(evaluate_case(case, expected_by_id[case["id"]], parent=root))
    return {
        "version": 1,
        "evaluation_kind": "PACT-owned synthetic regression, not blind A/B",
        "source_commit": "caller-recorded-current-P ACT-SHA",
        "case_count": len(results),
        "case_results": results,
        "task_queries_curated_with_fixture_knowledge": True,
        "owner_clarification_count": None,
        "owner_time_minutes": None,
        "owner_burden_reduction_verified": False,
        "real_agent_compatibility_verified": False,
        "release_attestation": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Local PACT-only synthetic Context evaluation")
    parser.add_argument("--inputs", default=str(CASES))
    parser.add_argument("--oracle", default=str(ORACLE))
    parser.add_argument("--output", help="optional output path; default stdout")
    args = parser.parse_args()
    inputs = json.loads(pathlib.Path(args.inputs).read_text(encoding="utf-8"))
    oracle = json.loads(pathlib.Path(args.oracle).read_text(encoding="utf-8"))
    report = evaluate(inputs, oracle)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        pathlib.Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
