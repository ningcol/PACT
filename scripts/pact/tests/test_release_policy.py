"""RC/stable release gates: malformed tags, missing reviewer audit or Owner GO fail closed."""
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


def rc_vars() -> dict:
    return {
        "PACT_RC_RELEASE_GO": "GO",
        "PACT_RC_RELEASE_APPROVED_SHA": SHA,
    }


def stable_vars() -> dict:
    return {
        "PACT_RELEASE_GO": "GO",
        "PACT_RELEASE_APPROVED_SHA": SHA,
        "PACT_AGENT_OWNER_GATES_APPROVED": "true",
    }


class ReleaseApprovalTests(unittest.TestCase):
    def gate(self, channel="rc", sha=SHA, main=SHA, env=None,
             approvals=None, ci=None, event="push"):
        return policy.require_release_approval(
            channel, sha, main,
            env=env if env is not None else rc_vars(),
            approvals=approvals if approvals is not None else approved(
                policy.ENVIRONMENT[channel]
            ),
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

    def test_rc_may_ship_for_trials_without_fake_agent_owner_claim(self):
        # RC has an explicit dedicated human review, SHA+GO, but not an
        # invented positive real Agent/Owner trial. Stable remains separate.
        self.gate(channel="rc")
        self.gate(channel="rc", env={
            **rc_vars(), "PACT_AGENT_OWNER_GATES_APPROVED": "false",
        })
        self.gate(channel="stable", env=stable_vars())

    def test_stable_cannot_use_rc_env_or_rc_variables(self):
        for approvals, vars_ in [
            (approved("pact-rc-approval"), stable_vars()),
            (approved("pact-release-approval"), rc_vars()),
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

    def test_unprotected_environment_or_bypass_cannot_release(self):
        for records in [
            [],
            {},
            None,
            [{"state": "approved", "environments": [
                {"name": "pact-rc-approval"}
            ]}],
            [{"state": "bypassed", "environments": [
                {"name": "pact-rc-approval"}
            ], "user": {"login": "owner", "type": "User"}}],
            [{"state": "rejected", "environments": [
                {"name": "pact-rc-approval"}
            ], "user": {"login": "owner", "type": "User"}}],
            approved("pact-release-approval"),
            [{"state": "approved", "environments": [
                {"name": "pact-rc-approval"}
            ], "user": {"login": "trusted-bot", "type": "Bot"}}],
        ]:
            with self.subTest(records=records):
                with self.assertRaises(policy.ReleaseHold):
                    self.gate(approvals=records)

    def test_failed_or_cross_sha_main_ci_cannot_release(self):
        for key in ("pact-check", "core-matrix"):
            bad = checked_ci()
            bad[key]["workflow_runs"][0]["conclusion"] = "failure"
            with self.assertRaises(policy.ReleaseHold):
                self.gate(ci=bad)
            bad = checked_ci()
            bad[key]["workflow_runs"][0]["head_sha"] = DIFFERENT_SHA
            with self.assertRaises(policy.ReleaseHold):
                self.gate(ci=bad)
            bad = checked_ci()
            bad[key]["workflow_runs"][0]["head_branch"] = "release-rc"
            with self.assertRaises(policy.ReleaseHold):
                self.gate(ci=bad)
            bad = checked_ci()
            bad[key]["workflow_runs"][0]["event"] = "pull_request"
            with self.assertRaises(policy.ReleaseHold):
                self.gate(ci=bad)
        with self.assertRaises(policy.ReleaseHold):
            self.gate(ci={})

    def test_missing_go_sha_and_event_always_block(self):
        with self.assertRaisesRegex(policy.ReleaseHold, "exact tag commit"):
            self.gate(env={"PACT_RC_RELEASE_GO": "GO"})
        with self.assertRaisesRegex(policy.ReleaseHold, "missing authenticated"):
            self.gate(approvals=[])
        with self.assertRaisesRegex(policy.ReleaseHold, "differs"):
            self.gate(main=DIFFERENT_SHA)
        with self.assertRaisesRegex(policy.ReleaseHold, "immutable version-tag push"):
            self.gate(event="workflow_dispatch")
        for sha in ("", "ab1", "n" * 40):
            with self.assertRaises(policy.ReleaseHold):
                self.gate(sha=sha, main=sha)

    def test_cli_classify_and_gates_remain_verifiable_offline(self):
        with tempfile.TemporaryDirectory() as td:
            folder = pathlib.Path(td)
            version = folder / "VERSION"
            version.write_text("0.4.0-rc.1\n")
            github_output = folder / "output.txt"
            with contextlib.redirect_stdout(io.StringIO()):
                code = policy.main([
                    "classify", "--tag", "v0.4.0-rc.1",
                    "--version-file", str(version),
                    "--github-output", str(github_output),
                ])
            self.assertEqual(code, 0)
            self.assertEqual(github_output.read_text().splitlines(), [
                "channel=rc",
                "environment=pact-rc-approval",
                "prerelease=true",
            ])
            files = {}
            for name, data in [
                ("approvals", approved("pact-rc-approval")),
                ("check", checked_ci()["pact-check"]),
                ("matrix", checked_ci()["core-matrix"]),
            ]:
                path = folder / (name + ".json")
                path.write_text(json.dumps(data))
                files[name] = str(path)
            argv = [
                "gate", "--tag", "v0.4.0-rc.1",
                "--version-file", str(version),
                "--tag-sha", SHA, "--main-sha", SHA,
                "--approvals-file", files["approvals"],
                "--check-runs-file", files["check"],
                "--matrix-runs-file", files["matrix"],
            ]
            with mock.patch.dict("os.environ", rc_vars(), clear=True):
                with contextlib.redirect_stdout(io.StringIO()) as buf:
                    self.assertEqual(policy.main(argv), 0)
                self.assertIn('"release_gate": "AUTHORIZED"', buf.getvalue())
            with mock.patch.dict("os.environ", {}, clear=True):
                with contextlib.redirect_stderr(io.StringIO()) as err:
                    self.assertEqual(policy.main(argv), 2)
                self.assertIn("Release HOLD", err.getvalue())


if __name__ == "__main__":
    unittest.main()
