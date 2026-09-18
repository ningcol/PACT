from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
RUNTIME = PROJECT_ROOT / "scripts" / "pact"
sys.path.insert(0, str(RUNTIME))

import code_map  # noqa: E402


class CodeLexicalIndexTests(unittest.TestCase):
    def write(self, suffix: str, text: str) -> pathlib.Path:
        temp = tempfile.NamedTemporaryFile(
            prefix="pact-code-lexical-",
            suffix=suffix,
            delete=False,
        )
        temp.close()
        path = pathlib.Path(temp.name)
        path.write_text(text, encoding="utf-8")
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        return path

    def test_js_member_identifiers_ignore_strings_and_comments(self) -> None:
        path = self.write(
            ".ts",
            """
            export async function publish(data) {
              const htmlContent = data.content;
              if (data.autoPublish) {
                return editor.innerHTML;
              }
              const text = "fake.commentOnly";
              const template = `fake.templateOnly`;
              // data.lineCommentOnly
              /* data.blockCommentOnly */
            }
            """,
        )

        symbols, imports, identifiers = code_map.parse_js_like(path)

        self.assertIn("publish", symbols)
        self.assertEqual(imports, [])
        self.assertIn("content", identifiers)
        self.assertIn("autoPublish", identifiers)
        self.assertIn("innerHTML", identifiers)
        self.assertNotIn("commentOnly", identifiers)
        self.assertNotIn("templateOnly", identifiers)
        self.assertNotIn("lineCommentOnly", identifiers)
        self.assertNotIn("blockCommentOnly", identifiers)

    def test_vue_identifier_index_reads_script_not_style(self) -> None:
        path = self.write(
            ".vue",
            """
            <template><div class="layout">Hello</div></template>
            <script setup lang="ts">
            if (state.autoPublish) {
              editor.innerHTML = state.content;
            }
            </script>
            <style>
            .fakeStyleIdentifier { color: red; }
            </style>
            """,
        )

        _symbols, _imports, identifiers = code_map.parse_js_like(path)

        self.assertIn("autoPublish", identifiers)
        self.assertIn("innerHTML", identifiers)
        self.assertIn("content", identifiers)
        self.assertNotIn("fakeStyleIdentifier", identifiers)

    def test_python_identifiers_come_from_ast(self) -> None:
        path = self.write(
            ".py",
            """
            def publish(data):
                if data.auto_publish:
                    return data.html_content
            """,
        )

        symbols, _imports, identifiers = code_map.parse_python(path)
        self.assertIn("publish", symbols)
        self.assertIn("auto_publish", identifiers)
        self.assertIn("html_content", identifiers)


if __name__ == "__main__":
    unittest.main()
