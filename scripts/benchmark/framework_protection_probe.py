#!/usr/bin/env python3
"""Opt-in, disposable macOS process-sandbox probe; never edit host settings.

The enclosing agent and remote/MCP tools are not placed in this sandbox.
Use the JSON coverage boundaries rather than interpreting PASS as host approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / ".pact/templates/security/macos-framework.sb"


def single_link_sources(paths: list[Path]) -> bool:
    """Necessary precondition, not a race-proof guarantee against an outside writer."""
    return all(path.is_file() and not path.is_symlink() and path.stat().st_nlink == 1
               for path in paths)


def probe() -> dict:
    sandbox = shutil.which("sandbox-exec")
    result = {
        "platform": platform.platform(), "python": sys.version.split()[0],
        "sandbox_client": sandbox, "policy": str(PROFILE.relative_to(ROOT)),
        "policy_sha256": hashlib.sha256(PROFILE.read_bytes()).hexdigest(),
        "actual_policy": "deny-default; process/read/sysctl/mach allowed; only fixture business/state writable",
        "checks": [], "host_agent_executed": False,
        "full_agent_strong_mode_verified": False,
        "coverage": {
            "sandboxed_python_and_children": "tested if probe passes",
            "entire_local_agent": "unverified",
            "native_file_tools": "unverified unless the entire host is launched inside the boundary",
            "mcp_plugins_remote_helpers": "unverified; outside processes are not constrained",
            "agent_loading_and_obedience": "unverified",
            "network_and_agent_credentials": "not exercised; sample policy denies network",
            "existing_organization_policy": "unchanged; no host/global config written",
        },
    }
    if sys.platform != "darwin" or not sandbox:
        result.update(status="unverified", reason="requires macOS sandbox-exec")
        return result
    with tempfile.TemporaryDirectory(prefix="pact-protection-") as tmp:
        base = Path(tmp).resolve()
        project = base / "project"
        business = project / "docs/product/specs"
        state = project / ".pact/tasks"
        business.mkdir(parents=True)
        state.mkdir(parents=True)
        launcher = project / "pact.py"
        runtime = project / ".pact/pact.pyz"
        version = project / ".pact/VERSION"
        policy = base / "policy.sb"
        policy.write_bytes(PROFILE.read_bytes())
        for file in (launcher, runtime, version):
            file.write_text("fixture protected bytes\n", encoding="utf-8")
        protected = [launcher, runtime, version, policy]
        before = {str(p): p.read_bytes() for p in protected}
        assert single_link_sources(protected)
        prefix = [sandbox, "-D", f"BUSINESS={business}", "-D", f"STATE={state}",
                  "-f", str(policy), sys.executable, "-c"]

        def run(name: str, code: str, expect_success: bool) -> None:
            child = subprocess.run(prefix + [code], capture_output=True, text=True,
                                   timeout=15)
            result["checks"].append({
                "name": name, "returncode": child.returncode,
                "expected": "allowed" if expect_success else "denied",
                "passed": (child.returncode == 0) if expect_success else (
                    child.returncode != 0 and "PermissionError" in child.stderr
                ),
                "stderr": child.stderr[-1200:],
            })

        run("framework-readable", f"from pathlib import Path; assert Path({str(runtime)!r}).read_bytes()", True)
        for file in protected:
            run("deny-write:" + file.name,
                f"from pathlib import Path; Path({str(file)!r}).write_text('changed')", False)
        (business / "new").write_text("replacement", encoding="utf-8")
        run("deny-replace-existing-source", f"import os; os.replace({str(business / 'new')!r}, {str(launcher)!r})", False)
        run("deny-unlink-runtime", f"import os; os.unlink({str(runtime)!r})", False)
        run("deny-rename-framework-parent", f"import os; os.rename({str(runtime.parent)!r}, {str(project / '.pact-old')!r})", False)
        run("deny-rename-project", f"import os; os.rename({str(project)!r}, {str(base / 'other')!r})", False)
        run("deny-hardlink-to-business", f"import os; os.link({str(runtime)!r}, {str(business / 'alias')!r})", False)
        run("deny-symlink-write", f"from pathlib import Path; p=Path({str(business / 'sym')!r}); p.symlink_to({str(runtime)!r}); p.write_text('changed')", False)
        run("business-and-state-writable", f"from pathlib import Path; Path({str(business / 'flow.md')!r}).write_text('body'); Path({str(state / 'receipt')!r}).write_text('state')", True)
        nested = "from pathlib import Path; Path(" + repr(str(runtime)) + ").write_text('child')"
        run("helper-inherits-denial", f"import subprocess,sys; sys.exit(subprocess.run([sys.executable,'-c',{nested!r}]).returncode)", False)
        result["protected_bytes_preserved"] = all(p.is_file() and p.read_bytes() == before[str(p)] for p in protected)
        result["business_body_verified"] = (business / "flow.md").read_text() == "body"
        result["execution_state_verified"] = (state / "receipt").read_text() == "state"
        # Pre-existing hardlink aliases can bypass path-only policies. The caller
        # must reject them before launch, rather than advertise an inode lock.
        os.link(runtime, business / "preexisting-alias")
        result["preexisting_hardlink_rejected_by_preflight"] = not single_link_sources(protected)
        result["concurrent_external_writers"] = "unverified; snapshot isolation and protected parent policy required"
        result["status"] = "pass" if (
            all(c["passed"] for c in result["checks"])
            and result["protected_bytes_preserved"]
            and result["business_body_verified"] and result["execution_state_verified"]
            and result["preexisting_hardlink_rejected_by_preflight"]
        ) else "fail"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    result = probe()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
