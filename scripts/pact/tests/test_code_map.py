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
            "import pkg.b\n\n"
            "class Service:\n"
            "    def dispatch(self):\n"
            "        def local_helper():\n"
            "            return 1\n"
            "        return local_helper()\n\n"
            "    async def refresh(self):\n"
            "        return 2\n\n"
            "def run():\n"
            "    return pkg.b.helper()\n",
        )

        data = self.build()
        by_path = {item["path"]: item for item in data["files"]}

        self.assertIn("Service", by_path["pkg/a.py"]["symbols"])
        self.assertIn("dispatch", by_path["pkg/a.py"]["symbols"])
        self.assertIn("refresh", by_path["pkg/a.py"]["symbols"])
        self.assertNotIn("local_helper", by_path["pkg/a.py"]["symbols"])
        self.assertIn("run", by_path["pkg/a.py"]["symbols"])
        edge = next(
            edge for edge in data["edges"]
            if edge["from"] == "pkg/a.py" and edge["to"] == "pkg/b.py"
        )
        self.assertEqual(edge["kind"], "import")
        self.assertEqual(edge["confidence"], "heuristic")

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

        edge = next(
            edge for edge in data["edges"]
            if edge["from"] == "src/a.ts" and edge["to"] == "src/b.ts"
        )
        self.assertEqual(edge["confidence"], "relative-resolved")
        test_edge = next(
            edge for edge in data["edges"]
            if edge["from"] == "src/a.test.ts" and edge["to"] == "src/a.ts"
        )
        self.assertEqual(test_edge["confidence"], "relative-resolved")
        self.assertTrue(by_path["src/a.test.ts"]["is_test"])
        self.assertIn("read", by_path["src/a.ts"]["symbols"])

    def test_vue_relative_import_is_resolved(self) -> None:
        self.write("src/widget.ts", "export const widget = 1;\n")
        self.write(
            "src/View.vue",
            '<script setup>\nimport { widget } from "./widget";\n</script>\n',
        )

        data = self.build()
        edge = next(
            edge for edge in data["edges"]
            if edge["from"] == "src/View.vue" and edge["to"] == "src/widget.ts"
        )
        self.assertEqual(edge["confidence"], "relative-resolved")

    def test_generic_go_and_swift_files_are_indexed_without_edges(self) -> None:
        self.write(
            "cmd/app/main.go",
            "package main\n\nfunc roundRobinDispatch() {}\n"
            "type clientState struct{}\n",
        )
        self.write(
            "ios/Player.swift",
            "final class AudioSessionCoordinator {\n"
            "    func activateSession() {}\n"
            "}\n",
        )

        data = self.build()
        by_path = {item["path"]: item for item in data["files"]}

        go = by_path["cmd/app/main.go"]
        self.assertEqual(go["language"], "go")
        self.assertEqual(go["parser_mode"], "generic-lexical")
        self.assertEqual(go["symbols"], [])
        self.assertEqual(go["imports"], [])
        self.assertIn("roundRobinDispatch", go["identifiers"])
        self.assertIn("clientState", go["identifiers"])

        swift = by_path["ios/Player.swift"]
        self.assertEqual(swift["language"], "swift")
        self.assertEqual(swift["parser_mode"], "generic-lexical")
        self.assertIn("AudioSessionCoordinator", swift["identifiers"])
        self.assertIn("activateSession", swift["identifiers"])

        generic_paths = {"cmd/app/main.go", "ios/Player.swift"}
        self.assertFalse(
            any(
                edge["from"] in generic_paths or edge["to"] in generic_paths
                for edge in data["edges"]
            )
        )

    def test_generic_identifiers_ignore_comments_and_strings(self) -> None:
        self.write(
            "server/main.go",
            """package server

// CommentOnlyIdentifier should not be indexed.
func RealHandler() string {
    return "StringOnlyIdentifier"
}

/* BlockOnlyIdentifier should also be ignored. */
""",
        )

        data = self.build()
        item = next(
            entry for entry in data["files"]
            if entry["path"] == "server/main.go"
        )

        self.assertIn("RealHandler", item["identifiers"])
        self.assertNotIn("CommentOnlyIdentifier", item["identifiers"])
        self.assertNotIn("StringOnlyIdentifier", item["identifiers"])
        self.assertNotIn("BlockOnlyIdentifier", item["identifiers"])

    def test_generic_test_path_detection_supports_go_style(self) -> None:
        self.write("tea_test.go", "package tea\nfunc TestUpdate() {}\n")
        data = self.build()
        item = next(entry for entry in data["files"] if entry["path"] == "tea_test.go")
        self.assertTrue(item["is_test"])
        self.assertEqual(item["parser_mode"], "generic-lexical")

    def test_generic_file_is_not_used_for_js_import_resolution(self) -> None:
        self.write("src/bridge.go", "package bridge\nfunc Bridge() {}\n")
        self.write(
            "src/app.ts",
            'import { Bridge } from "./bridge";\nexport const app = Bridge;\n',
        )

        data = self.build()
        self.assertFalse(
            any(
                edge["from"] == "src/app.ts"
                and edge["to"] == "src/bridge.go"
                for edge in data["edges"]
            )
        )
        app = next(item for item in data["files"] if item["path"] == "src/app.ts")
        bridge_import = next(
            item for item in app["imports"] if item["raw"] == "./bridge"
        )
        self.assertIsNone(bridge_import["resolved"])

    def test_excluded_directories_are_not_indexed(self) -> None:
        self.write("node_modules/pkg/index.js", "export const hidden = true;\n")
        self.write("src/visible.js", "export const visible = true;\n")

        data = self.build()
        paths = {item["path"] for item in data["files"]}

        self.assertIn("src/visible.js", paths)
        self.assertNotIn("node_modules/pkg/index.js", paths)


if __name__ == "__main__":
    unittest.main()
