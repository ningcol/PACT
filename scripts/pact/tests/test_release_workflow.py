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
        self.assertIn("test_streaming_reliability.py", text)

    def test_release_marks_version_suffixes_as_prerelease(self) -> None:
        text = RELEASE.read_text(encoding="utf-8")

        self.assertIn("prerelease={'true' if '-' in version else 'false'}", text)
        self.assertIn("IS_PRERELEASE:", text)
        self.assertIn("EXTRA_ARGS+=(--prerelease)", text)
        self.assertIn('test "$TAG_VERSION" = "$RUNTIME_VERSION"', text)

    def test_release_keeps_publish_permission_scoped_to_release_job(self) -> None:
        text = RELEASE.read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read", text)
        self.assertIn("release:\n    needs:", text)
        self.assertIn("contents: write", text)


if __name__ == "__main__":
    unittest.main()
