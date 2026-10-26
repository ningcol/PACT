from __future__ import annotations

import pathlib
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
RELEASE = PROJECT_ROOT / ".github" / "workflows" / "release.yml"


class ReleaseWorkflowContractTests(unittest.TestCase):
    def test_release_is_gated_by_full_portability_matrix(self) -> None:
        text = RELEASE.read_text(encoding="utf-8")

        self.assertIn("portability:", text)
        self.assertIn("ubuntu-latest", text)
        self.assertIn("macos-latest", text)
        self.assertIn("windows-latest", text)
        for version in ["3.11", "3.12", "3.13"]:
            self.assertIn(f'- "{version}"', text)

        self.assertIn("needs:", text)
        self.assertIn("- portability", text)
        self.assertIn(
            "python -m unittest discover -s scripts/pact/tests -p 'test_*.py'",
            text,
        )

    def test_release_marks_version_suffixes_as_prerelease(self) -> None:
        text = RELEASE.read_text(encoding="utf-8")

        self.assertIn("scripts/release/release_policy.py classify", text)
        self.assertIn("needs.classify.outputs.prerelease", text)
        self.assertIn("IS_PRERELEASE:", text)
        self.assertIn("EXTRA_ARGS+=(--prerelease --latest=false)", text)
        self.assertIn("scripts/release/release_policy.py gate", text)

    def test_release_keeps_publish_permission_scoped_to_release_job(self) -> None:
        text = RELEASE.read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read", text)
        self.assertIn("release:\n    needs:", text)
        self.assertIn("contents: write", text)

    def test_rc_needs_no_environment_but_stable_requires_real_review(self) -> None:
        text = RELEASE.read_text(encoding="utf-8")
        stable, publish = text.split("\n  stable_approval:\n", 1)[1].split(
            "\n  release:\n", 1
        )
        self.assertIn("if: ${{ needs.classify.outputs.channel == 'stable' }}", stable)
        self.assertIn("environment: pact-release-approval", stable)
        self.assertIn("PACT_RELEASE_GO:", stable)
        self.assertIn("PACT_RELEASE_APPROVED_SHA:", stable)
        self.assertIn("PACT_AGENT_OWNER_GATES_APPROVED:", stable)
        self.assertIn("actions/runs/$GITHUB_RUN_ID/approvals", stable)
        self.assertIn("scripts/release/release_policy.py gate", stable)
        self.assertNotIn("environment: ${{ needs.classify.outputs.environment }}", text)
        self.assertNotIn("environment: pact-rc-approval", text)
        self.assertNotIn("PACT_RC_RELEASE_GO:", text)
        self.assertNotIn("PACT_RC_RELEASE_APPROVED_SHA:", text)
        self.assertIn("needs.stable_approval.result == 'skipped'", publish)
        self.assertIn("needs.stable_approval.result == 'success'", publish)
        self.assertIn("needs.classify.result == 'success'", publish)
        self.assertIn("needs.portability.result == 'success'", publish)
        self.assertIn("!cancelled()", publish)
        self.assertIn("if: ${{ needs.classify.outputs.channel == 'rc' }}", publish)
        self.assertIn("scripts/release/release_policy.py gate", publish)
        self.assertIn("git ls-remote --exit-code origin refs/heads/main", publish)
        self.assertIn('test "$TAG_SHA" = "$MAIN_SHA"', publish)
        self.assertIn("actions/workflows/pact-check.yml/runs?head_sha=$TAG_SHA", publish)
        self.assertIn("actions/workflows/core-matrix.yml/runs?head_sha=$TAG_SHA", publish)
        self.assertLess(
            text.index("scripts/release/release_policy.py gate"),
            text.index("gh release create"),
        )
        policy_text = (
            PROJECT_ROOT / "scripts/release/release_policy.py"
        ).read_text(encoding="utf-8")
        for gate in (
            "PACT_RELEASE_GO",
            "PACT_RELEASE_APPROVED_SHA",
            "PACT_AGENT_OWNER_GATES_APPROVED",
            "pact-release-approval",
        ):
            self.assertIn(gate, policy_text)
        self.assertNotIn("PACT_RC_RELEASE_APPROVED_SHA", policy_text)
        self.assertNotIn("PACT_RC_RELEASE_GO", policy_text)

    def test_release_builds_and_smokes_exact_assets_before_publish(self) -> None:
        text = RELEASE.read_text(encoding="utf-8")

        self.assertIn(
            "python scripts/release/release_assets.py --output-dir dist --smoke",
            text,
        )
        self.assertNotIn(
            "python scripts/pact/runtime_bundle.py --output dist/pact.pyz",
            text,
        )
        publish_index = text.index("gh release create")
        smoke_index = text.index(
            "python scripts/release/release_assets.py --output-dir dist --smoke"
        )
        self.assertLess(smoke_index, publish_index)


if __name__ == "__main__":
    unittest.main()
