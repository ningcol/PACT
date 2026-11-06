"""Bounded identity diagnostics for the runtime currently serving a project."""
from __future__ import annotations

import pathlib

from distribution import read_install_manifest, resolve_install_target, sha256_file


CAPABILITIES = (
    "knowledge-retention-review", "domain-audit", "workspace-staleness-detail",
    "mechanical-owner-draft", "coverage-review-draft", "chinese-registered-phrase",
    "task-generation-history", "runtime-agent-guidance",
)


def runtime_identity(root: pathlib.Path) -> dict:
    result = {"version": "unknown", "sha256": None, "integrity": "unknown",
              "capabilities": list(CAPABILITIES), "errors": []}
    try:
        version = resolve_install_target(root, ".pact/VERSION")
        if version.is_file():
            result["version"] = version.read_text(encoding="utf-8").strip()
        bundle = resolve_install_target(root, ".pact/pact.pyz")
        manifest = read_install_manifest(root)
        if bundle.exists() and not bundle.is_file():
            raise ValueError("runtime archive must be a regular file")
        if not bundle.is_file():
            result["integrity"] = "source" if manifest is None else "missing"
            return result
        result["sha256"] = sha256_file(bundle)
        record = (manifest or {}).get("files", {}).get(".pact/pact.pyz")
        if record is None:
            result["integrity"] = "untracked"
        else:
            result["integrity"] = "matched" if (
                record.get("management") == "framework"
                and record.get("installed_sha256") == result["sha256"]
                and manifest["runtime_version"] == result["version"]
            ) else "mismatch"
    except (OSError, ValueError, UnicodeError) as exc:
        result["integrity"] = "error"
        result["errors"].append(str(exc))
    return result
