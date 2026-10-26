"""RC publishes on reviewed main CI; stable retains protected human approval."""
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "release"))
import release_policy as policy

SHA = "a" * 40
DIFFERENT_SHA = "b" * 40
UNSET = object()


def checked_ci(sha: str = SHA) -> dict:
    return {
        "pact-check": {
            "workflow_runs": [{
                "name": "PACT Check", "head_sha": sha, "head_branch": "main",
                "event": "push", "status": "completed", "conclusion": "success",
            }],
        },
        "core-matrix": {
            "workflow_runs": [{
                "name": "PACT Core Matrix", "head_sha": sha, "head_branch": "main",
                "event": "push", "status": "completed", "conclusion": "success",
            }],
        },
    }


def approved(environment: str) -> list:
    return [{
        "state": "approved",
        "user": {"login": "reviewing-owner", "type": "User"},
        "environments": [{"name": environment, "id": 27}],
    }]


def stable_vars() -> dict:
    return {
        "PACT_RELEASE_GO": "GO",
        "PACT_RELEASE_APPROVED_SHA": SHA,
        "PACT_AGENT_OWNER_GATES_APPROVED": "true",
    }


class ReleaseApprovalTests(unittest.TestCase):
    def gate(self, channel="rc", sha=SHA, main=SHA, env=None,
             approvals=UNSET, ci=None, event="push"):
        return policy.require_release_approval(
            channel, sha, main,
            env=env if env is not None else (
                stable_vars() if channel == "stable" else {}
            ),
            approvals=(
                approved(policy.ENVIRONMENT["stable"]) if channel == "stable" else None
            ) if approvals is UNSET else approvals,
            ci_reports=ci if ci is not None else checked_ci(),
            event=event,
        )

    def test_rc_and_stable_classification_is_version_exact(self):
        self.assertEqual(policy.classify("v0.4.0-rc.1", "0.4.0-rc.1"), "rc")
        self.assertEqual(policy.classify("v0.4.0", "0.4.0"), "stable")
        self.assertEqual(policy.classify("v10.32.5-rc.10", "10.32.5-rc.10"), "rc")
        for tag, version in [
            ("v0.4.0-rc.1", "0.4.0"),
            ("v0.4.0", "0.4.0-rc.1"),
            ("v0.4.0-dev.1", "0.4.0-dev.1"),
            ("v0.4.0-alpha", "0.4.0-alpha"),
            ("v0.04.0", "0.04.0"),
            ("v0.4.0-rc.01", "0.4.0-rc.01"),
            ("v0.4.0\nowner", "0.4.0\nowner"),
            ("main", "main"),
            ("v0.4.0+latest", "0.4.0+latest"),
        ]:
            with self.subTest(tag=tag):
                with self.assertRaises(policy.ReleaseHold):
                    policy.classify(tag, version)

    def test_rc_publish_requires_no_environment_owner_go_or_agent_claim(self):
        self.gate(channel="rc", env={}, approvals=None)
        self.gate(channel="rc", env={}, approvals=[])
        self.gate(channel="rc", env={}, approvals={"untrusted": True})
        self.gate(channel="rc", env={
            "PACT_AGENT_OWNER_GATES_APPROVED": "false",
        })
        self.gate(channel="stable", env=stable_vars())

    def test_stable_cannot_use_unprotected_env_or_missing_owner_go(self):
        for approvals, vars_ in [
            (approved("pact-rc-approval"), stable_vars()),
            (approved("pact-release-approval"), {}),
            (approved("pact-release-approval"), {
                **stable_vars(), "PACT_AGENT_OWNER_GATES_APPROVED": "false",
            }),
            (approved("pact-release-approval"), {
                **stable_vars(), "PACT_RELEASE_APPROVED_SHA": DIFFERENT_SHA,
            }),
        ]:
            with self.subTest(vars=vars_, approvals=approvals):
                with self.assertRaises(policy.ReleaseHold):
                    self.gate("stable", env=vars_, approvals=approvals)

    def test_stable_unprotected_environment_or_bypass_cannot_release(self):
        for records in [
            [], {}, None,
            [{"state": "approved", "environments": [
                {"name": "pact-release-approval"},
            ]}],
            [{"state": "bypassed", "environments": [
                {"name": "pact-release-approval"},
            ], "user": {"login": "owner", "type": "User"}}],
            [{"state": "rejected", "environments": [
                {"name": "pact-release-approval"},
            ], "user": {"login": "owner", "type": "User"}}],
            approved("pact-rc-approval"),
            [{"state": "approved", "environments": [
                {"name": "pact-release-approval"},
            ], "user": {"login": "bot", "type": "Bot"}}],
        ]:
            with self.subTest(records=records):
                with self.assertRaises(policy.ReleaseHold):
                    self.gate(channel="stable", env=stable_vars(), approvals=records)

    def test_both_channels_reject_failed_cross_sha_or_non_main_push_ci(self):
        for channel in ("rc", "stable"):
            for key in ("pact-check", "core-matrix"):
                for field, bad_value in [
                    ("conclusion", "failure"),
                    ("head_sha", DIFFERENT_SHA),
                    ("head_branch", "release-rc"),
                    ("event", "pull_request"),
                    ("status", "in_progress"),
                ]:
                    with self.subTest(channel=channel, key=key, field=field):
                        bad = checked_ci()
                        bad[key]["workflow_runs"][0][field] = bad_value
                        with self.assertRaises(policy.ReleaseHold):
                            self.gate(channel=channel, ci=bad)
            with self.assertRaises(policy.ReleaseHold):
                self.gate(channel=channel, ci={})

    def test_stable_missing_go_and_both_channels_wrong_sha_or_event_block(self):
        for vars_ in [
            {},
            {"PACT_RELEASE_GO": "GO"},
            {**stable_vars(), "PACT_RELEASE_GO": "WAIT"},
            {**stable_vars(), "PACT_RELEASE_APPROVED_SHA": DIFFERENT_SHA},
            {**stable_vars(), "PACT_AGENT_OWNER_GATES_APPROVED": "false"},
        ]:
            with self.subTest(vars=vars_):
                with self.assertRaises(policy.ReleaseHold):
                    self.gate("stable", env=vars_)
        for channel in ("rc", "stable"):
            with self.assertRaisesRegex(policy.ReleaseHold, "differs"):
                self.gate(channel=channel, main=DIFFERENT_SHA)
            with self.assertRaisesRegex(policy.ReleaseHold, "immutable version-tag push"):
                self.gate(channel=channel, event="workflow_dispatch")
            for sha in ("", "ab1", "n" * 40):
                with self.assertRaises(policy.ReleaseHold):
                    self.gate(channel=channel, sha=sha, main=sha)

    def test_workflow_stable_approval_cannot_be_bypassed_for_release(self):
        raw = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        protected, publish = raw.split("\n  stable_approval:\n", 1)[1].split(
            "\n  release:\n", 1
        )
        self.assertIn("environment: pact-release-approval", protected)
        self.assertIn("PACT_RELEASE_APPROVED_SHA:", protected)
        self.assertIn("PACT_AGENT_OWNER_GATES_APPROVED:", protected)
        self.assertIn("actions/runs/$GITHUB_RUN_ID/approvals", protected)
        self.assertIn("scripts/release/release_policy.py gate", protected)
        self.assertNotIn("environment:", publish.replace(
            "# No Environment needed for RC; stable approval occurs in stable_approval.",
            "",
        ))
        self.assertIn("needs.stable_approval.result == 'skipped'", publish)
        self.assertIn("needs.stable_approval.result == 'success'", publish)
        self.assertIn("needs.portability.result == 'success'", publish)
        self.assertIn("!cancelled()", publish)
        self.assertIn("needs.classify.outputs.channel == 'rc'", publish)
        self.assertIn("needs.classify.outputs.channel == 'stable'", publish)
        self.assertNotIn("PACT_RC_RELEASE_GO:", raw)
        self.assertNotIn("PACT_RC_RELEASE_APPROVED_SHA:", raw)
        self.assertIn("actions/workflows/pact-check.yml/runs?head_sha=$TAG_SHA", raw)
        self.assertIn("actions/workflows/core-matrix.yml/runs?head_sha=$TAG_SHA", raw)
        self.assertLess(raw.index("scripts/release/release_policy.py gate"),
                        raw.index("gh release create"))
        self.assertIn("--verify-tag", raw)
        self.assertIn("--prerelease --latest=false", raw)
        self.assertIn("EXPERIMENTAL RC FOR REAL-PROJECT PILOTS ONLY", raw)
        for asset in ("dist/SHA256SUMS", "dist/LICENSE", "dist/pact.pyz"):
            self.assertIn(asset, raw)
        self.assertIn("python scripts/release/release_assets.py --output-dir dist --smoke", raw)
        for version in ("3.11", "3.12", "3.13"):
            self.assertIn(version, raw)
        for runner in ("windows-latest", "macos-latest", "ubuntu-latest"):
            self.assertIn(runner, raw)

    def test_cli_classify_rc_and_stable_gates_remain_verifiable_offline(self):
        with tempfile.TemporaryDirectory() as td:
            folder = pathlib.Path(td)
            version = folder / "VERSION"
            version.write_text("0.4.0-rc.1\n")
            github_output = folder / "output.txt"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(policy.main([
                    "classify", "--tag", "v0.4.0-rc.1",
                    "--version-file", str(version),
                    "--github-output", str(github_output),
                ]), 0)
            self.assertEqual(github_output.read_text().splitlines(), [
                "channel=rc", "prerelease=true",
            ])
            files = {}
            for name, data in [
                ("approvals", approved("pact-release-approval")),
                ("check", checked_ci()["pact-check"]),
                ("matrix", checked_ci()["core-matrix"]),
            ]:
                path = folder / (name + ".json")
                path.write_text(json.dumps(data))
                files[name] = str(path)
            base = [
                "--tag-sha", SHA, "--main-sha", SHA,
                "--check-runs-file", files["check"],
                "--matrix-runs-file", files["matrix"],
            ]
            rc = [
                "gate", "--tag", "v0.4.0-rc.1",
                "--version-file", str(version), *base,
            ]
            with mock.patch.dict("os.environ", {}, clear=True):
                with contextlib.redirect_stdout(io.StringIO()) as result:
                    self.assertEqual(policy.main(rc), 0)
                output = json.loads(result.getvalue())
                self.assertEqual(output["channel"], "rc")
                self.assertNotIn("reviewed_environment", output)
            version.write_text("0.4.0\n")
            stable = [
                "gate", "--tag", "v0.4.0",
                "--version-file", str(version), *base,
            ]
            with mock.patch.dict("os.environ", stable_vars(), clear=True):
                with contextlib.redirect_stderr(io.StringIO()) as err:
                    self.assertEqual(policy.main(stable), 2)
                self.assertIn("stable requires an authenticated approvals file", err.getvalue())
                with contextlib.redirect_stdout(io.StringIO()) as result:
                    self.assertEqual(policy.main([
                        *stable, "--approvals-file", files["approvals"],
                    ]), 0)
                self.assertEqual(
                    json.loads(result.getvalue())["reviewed_environment"],
                    "pact-release-approval",
                )
            with mock.patch.dict("os.environ", {}, clear=True):
                with contextlib.redirect_stderr(io.StringIO()) as err:
                    self.assertEqual(policy.main([
                        *stable, "--approvals-file", files["approvals"],
                    ]), 2)
                self.assertIn("Release HOLD", err.getvalue())



if __name__ == "__main__":
    unittest.main()
