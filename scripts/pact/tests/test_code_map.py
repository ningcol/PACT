from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
CODE_MAP = PROJECT_ROOT / "scripts" / "pact" / "code_map.py"
SCHEMA = PROJECT_ROOT / ".pact" / "schema" / "code-map.schema.json"


class CodeMapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-code-map-test-")
        self.root = pathlib.Path(self.temp.name)
        schema_dir = self.root / ".pact" / "schema"
        schema_dir.mkdir(parents=True)
        shutil.copy2(SCHEMA, schema_dir / "code-map.schema.json")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def build(self) -> dict:
        output = self.root / ".pact" / "cache" / "code-map.json"
        result = subprocess.run(
            [
                sys.executable,
                str(CODE_MAP),
                "--root",
                str(self.root),
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(output.read_text(encoding="utf-8"))

    def test_python_symbols_and_import_edge(self) -> None:
        self.write("pkg/b.py", "def helper():\n    return 1\n")
        self.write(
            "pkg/a.py",
            "import pkg.b\n\nclass Service:\n    pass\n\ndef run():\n    return pkg.b.helper()\n",
        )

        data = self.build()
        by_path = {item["path"]: item for item in data["files"]}

        self.assertIn("Service", by_path["pkg/a.py"]["symbols"])
        self.assertIn("run", by_path["pkg/a.py"]["symbols"])
        self.assertIn(
            {"from": "pkg/a.py", "to": "pkg/b.py", "kind": "import"},
            data["edges"],
        )

    def test_typescript_relative_import_and_test_detection(self) -> None:
        self.write("src/b.ts", "export const value = 1;\n")
        self.write(
            "src/a.ts",
            'import { value } from "./b";\nexport function read() { return value; }\n',
        )
        self.write(
            "src/a.test.ts",
            'import { read } from "./a";\nexport const result = read();\n',
        )

        data = self.build()
        by_path = {item["path"]: item for item in data["files"]}

        self.assertIn(
            {"from": "src/a.ts", "to": "src/b.ts", "kind": "import"},
            data["edges"],
        )
        self.assertIn(
            {"from": "src/a.test.ts", "to": "src/a.ts", "kind": "import"},
            data["edges"],
        )
        self.assertTrue(by_path["src/a.test.ts"]["is_test"])
        self.assertIn("read", by_path["src/a.ts"]["symbols"])

    def test_vue_relative_import_is_resolved(self) -> None:
        self.write("src/widget.ts", "export const widget = 1;\n")
        self.write(
            "src/View.vue",
            '<script setup>\nimport { widget } from "./widget";\n</script>\n',
        )

        data = self.build()
        self.assertIn(
            {"from": "src/View.vue", "to": "src/widget.ts", "kind": "import"},
            data["edges"],
        )

    def test_excluded_directories_are_not_indexed(self) -> None:
        self.write("node_modules/pkg/index.js", "export const hidden = true;\n")
        self.write("src/visible.js", "export const visible = true;\n")

        data = self.build()
        paths = {item["path"] for item in data["files"]}

        self.assertIn("src/visible.js", paths)
        self.assertNotIn("node_modules/pkg/index.js", paths)


if __name__ == "__main__":
    unittest.main()
