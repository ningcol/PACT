from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
MAP = PROJECT_ROOT / "scripts" / "pact" / "map.py"
CODE_MAP = PROJECT_ROOT / "scripts" / "pact" / "code_map.py"
CODE_SCHEMA = PROJECT_ROOT / ".pact" / "schema" / "code-map.schema.json"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AdoptedDiscoveryOwnershipTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-ownership-test-")
        self.root = pathlib.Path(self.temp.name)
        schema_dir = self.root / ".pact" / "schema"
        schema_dir.mkdir(parents=True)
        shutil.copy2(CODE_SCHEMA, schema_dir / "code-map.schema.json")

        self.write("README.md", "# Target Project\n")
        self.write("src/app.py", "def target_feature():\n    return 'target'\n")
        self.write(
            "scripts/pact/runtime.py",
            "def pact_internal():\n    return 'framework'\n",
        )
        self.write(
            "docs/governance/constitution.md",
            "# Generic PACT Constitution\n",
        )

        manifest = {
            "format_version": 1,
            "runtime_version": "test",
            "files": {
                "scripts/pact/runtime.py": {
                    "management": "framework",
                    "source_path": "scripts/pact/runtime.py",
                    "source_sha256": sha256(self.root / "scripts/pact/runtime.py"),
                    "installed_sha256": sha256(self.root / "scripts/pact/runtime.py"),
                },
                "docs/governance/constitution.md": {
                    "management": "seed",
                    "source_path": "docs/governance/constitution.md",
                    "source_sha256": sha256(
                        self.root / "docs/governance/constitution.md"
                    ),
                    "installed_sha256": sha256(
                        self.root / "docs/governance/constitution.md"
                    ),
                },
            },
        }
        self.write(
            ".pact/install.json",
            json.dumps(manifest, indent=2) + "\n",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, relative: str, content: str) -> pathlib.Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def run_map(self) -> dict:
        output = self.root / ".pact" / "cache" / "project-map.json"
        result = subprocess.run(
            [
                sys.executable,
                str(MAP),
                "--root",
                str(self.root),
                "--output",
                str(output),
                "--ensure",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(output.read_text(encoding="utf-8"))

    def run_code_map(self) -> dict:
        output = self.root / ".pact" / "cache" / "code-map.json"
        result = subprocess.run(
            [
                sys.executable,
                str(CODE_MAP),
                "--root",
                str(self.root),
                "--output",
                str(output),
                "--ensure",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(output.read_text(encoding="utf-8"))

    def test_framework_runtime_and_untouched_seed_are_excluded(self) -> None:
        project = self.run_map()
        paths = {item["path"] for item in project["documents"]}

        self.assertIn("README.md", paths)
        self.assertNotIn("docs/governance/constitution.md", paths)

        code = self.run_code_map()
        code_paths = {item["path"] for item in code["files"]}

        self.assertIn("src/app.py", code_paths)
        self.assertNotIn("scripts/pact/runtime.py", code_paths)

    def test_modified_seed_becomes_project_knowledge(self) -> None:
        first = self.run_map()
        first_paths = {item["path"] for item in first["documents"]}
        self.assertNotIn("docs/governance/constitution.md", first_paths)

        self.write(
            "docs/governance/constitution.md",
            "# Project-specific Constitution\n\nCustom rule.\n",
        )

        second = self.run_map()
        second_paths = {item["path"] for item in second["documents"]}
        self.assertIn("docs/governance/constitution.md", second_paths)

    def test_framework_file_stays_excluded_even_if_locally_modified(self) -> None:
        self.write(
            "scripts/pact/runtime.py",
            "def pact_internal():\n    return 'locally-modified-framework'\n",
        )

        code = self.run_code_map()
        code_paths = {item["path"] for item in code["files"]}
        self.assertNotIn("scripts/pact/runtime.py", code_paths)


if __name__ == "__main__":
    unittest.main()
