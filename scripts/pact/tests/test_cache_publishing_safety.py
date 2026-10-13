"""Stage 8 RED: disposable index structural integrity and atomic publication.

Exercises real Project/Code Map CLI entry points in a scratch project, plus
fault-injected writer/readers. No third-party packages or external services.
"""

from __future__ import annotations

import contextlib
from concurrent.futures import ThreadPoolExecutor
import copy
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
RUNTIME = PROJECT_ROOT / "scripts" / "pact"
sys.path.insert(0, str(RUNTIME))
import cache as cache_runtime
import code_map as code_index
import map as project_map
import parse_cache as parse_runtime


class CachePublishingSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-cache-safety-")
        self.root = pathlib.Path(self.temp.name) / "project"
        self.root.mkdir()
        self.write("README.md", "# Product knowledge\n\nKnown behavior.\n")
        self.write("docs/guide.md", "# Guide\n\nMore project knowledge.\n")
        self.write(
            "src/app.py", "import src.helper\n\ndef target_function():\n    return 7\n"
        )
        self.write("src/helper.py", "def helper():\n    return 7\n")
        schema = self.root / ".pact" / "schema"
        schema.mkdir(parents=True)
        shutil.copyfile(
            PROJECT_ROOT / ".pact" / "schema" / "code-map.schema.json",
            schema / "code-map.schema.json",
        )
        self.map_path = self.root / ".pact" / "cache" / "project-map.json"
        self.code_path = self.root / ".pact" / "cache" / "code-map.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, relative: str, content: str) -> pathlib.Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def run_builder(self, script: str) -> tuple[dict, str]:
        output = self.map_path if script == "map" else self.code_path
        process = subprocess.run(
            [
                sys.executable, str(RUNTIME / f"{script}.py"), "--root",
                str(self.root), "--output", str(output), "--ensure",
            ],
            capture_output=True, text=True, timeout=50,
        )
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        return json.loads(output.read_text(encoding="utf-8")), process.stdout

    def run_in_process(self, script: str) -> int:
        output = self.map_path if script == "map" else self.code_path
        module = project_map if script == "map" else code_index
        with (
            mock.patch.object(
                sys, "argv",
                [f"{script}.py", "--root", str(self.root), "--output", str(output)],
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            return module.main()

    def test_project_map_missing_documents_rebuilds_not_fresh(self) -> None:
        original, _ = self.run_builder("map")
        damaged = copy.deepcopy(original)
        del damaged["documents"]
        self.map_path.write_text(json.dumps(damaged) + "\n", encoding="utf-8")
        repaired, log = self.run_builder("map")
        self.assertIn("README.md", [d["path"] for d in repaired["documents"]])
        self.assertNotIn("fresh ->", log)

    def test_project_map_wrong_document_paths_rebuilds_even_if_list_is_valid(self) -> None:
        original, _ = self.run_builder("map")
        damaged = copy.deepcopy(original)
        damaged["documents"] = []
        self.map_path.write_text(json.dumps(damaged) + "\n", encoding="utf-8")
        repaired, log = self.run_builder("map")
        self.assertIn("README.md", [d["path"] for d in repaired["documents"]])
        self.assertNotIn("fresh ->", log)

    def test_project_map_missing_id_map_or_wrong_document_type_rebuilds(self) -> None:
        self.run_builder("map")
        for bad_key, replacement in (("id_to_path", []), ("documents", {})):
            with self.subTest(bad_key=bad_key):
                pristine, _ = self.run_builder("map")
                damaged = copy.deepcopy(pristine)
                damaged[bad_key] = replacement
                self.map_path.write_text(
                    json.dumps(damaged) + "\n", encoding="utf-8"
                )
                fixed, _ = self.run_builder("map")
                self.assertIsInstance(fixed["id_to_path"], dict)
                self.assertIsInstance(fixed["documents"], list)
                self.assertTrue(fixed["documents"])

    def test_code_map_missing_files_and_edges_rebuilds_using_schema(self) -> None:
        initial, _ = self.run_builder("code_map")
        self.assertTrue(initial["files"])
        self.assertTrue(initial["edges"])
        for field in ("files", "edges"):
            with self.subTest(field=field):
                original, _ = self.run_builder("code_map")
                damaged = copy.deepcopy(original)
                del damaged[field]
                self.code_path.write_text(
                    json.dumps(damaged) + "\n", encoding="utf-8"
                )
                repaired, log = self.run_builder("code_map")
                self.assertTrue(repaired["files"])
                self.assertTrue(repaired["edges"])
                self.assertNotIn("fresh ->", log)

    def test_code_map_empty_valid_files_list_must_not_shadow_real_sources(self) -> None:
        valid, _ = self.run_builder("code_map")
        valid["files"] = []
        valid["edges"] = []
        self.code_path.write_text(json.dumps(valid) + "\n", encoding="utf-8")
        repaired, log = self.run_builder("code_map")
        self.assertIn("src/app.py", [entry["path"] for entry in repaired["files"]])
        self.assertNotIn("fresh ->", log)

    def test_project_parse_cache_rechecks_modified_parsed_payload(self) -> None:
        self.run_builder("map")
        cache_path = self.root / ".pact" / "cache" / "project-file-cache.json"
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        self.assertIn("README.md", cache["entries"])
        cache["entries"]["README.md"]["parsed"]["title"] = "Forged cached title"
        cache_path.write_text(json.dumps(cache) + "\n", encoding="utf-8")
        self.map_path.unlink()  # force rebuild through the parse cache
        restored, _ = self.run_builder("map")
        title = next(d["title"] for d in restored["documents"] if d["path"] == "README.md")
        self.assertEqual(title, "Product knowledge")

    def test_code_parse_cache_rechecks_modified_parsed_payload(self) -> None:
        self.run_builder("code_map")
        cache_path = self.root / ".pact" / "cache" / "code-file-cache.json"
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        self.assertIn("src/app.py", cache["entries"])
        cache["entries"]["src/app.py"]["parsed"]["symbols"].append("INJECTED_SYMBOL")
        cache_path.write_text(json.dumps(cache) + "\n", encoding="utf-8")
        self.code_path.unlink()
        restored, _ = self.run_builder("code_map")
        item = next(d for d in restored["files"] if d["path"] == "src/app.py")
        self.assertNotIn("INJECTED_SYMBOL", item["symbols"])

    def test_healthy_cache_remains_reused_and_unchanged(self) -> None:
        for name in ("map", "code_map"):
            with self.subTest(name=name):
                original, _ = self.run_builder(name)
                second, log = self.run_builder(name)
                self.assertIn("fresh ->", log)
                self.assertEqual(second, original)

    def test_partial_project_map_write_cannot_destroy_previous_valid_json(self) -> None:
        self.run_builder("map")
        self.write("README.md", "# Changed\n\nNew content\n")
        self.assert_interrupted_index_write_keeps_valid_old_or_new("map")

    def test_partial_code_map_write_cannot_destroy_previous_valid_json(self) -> None:
        self.run_builder("code_map")
        self.write("src/app.py", "def changed_symbol():\n    return 9\n")
        self.assert_interrupted_index_write_keeps_valid_old_or_new("code_map")

    def assert_interrupted_index_write_keeps_valid_old_or_new(self, script: str) -> None:
        index = self.map_path if script == "map" else self.code_path
        original_write = pathlib.Path.write_text

        def fail_after_partial(path, text, *args, **kwargs):
            if path == index:
                with path.open("w", encoding="utf-8") as handle:
                    handle.write('{"partial":')
                raise OSError("simulated partial index publication")
            return original_write(path, text, *args, **kwargs)

        with mock.patch.object(
            pathlib.Path, "write_text", autospec=True, side_effect=fail_after_partial
        ):
            try:
                self.run_in_process(script)
            except OSError:
                pass

        data = json.loads(index.read_text(encoding="utf-8"))
        expected_key = "documents" if script == "map" else "files"
        self.assertIn(expected_key, data)

    def test_partial_parse_cache_write_cannot_destroy_previous_valid_json(self) -> None:
        self.run_builder("map")
        target = self.root / ".pact" / "cache" / "project-file-cache.json"
        original_write = pathlib.Path.write_text

        def fail_after_partial(path, text, *args, **kwargs):
            if path == target:
                with path.open("w", encoding="utf-8") as handle:
                    handle.write('{"partial":')
                raise OSError("simulated partial per-file cache")
            return original_write(path, text, *args, **kwargs)

        with mock.patch.object(
            pathlib.Path, "write_text", autospec=True, side_effect=fail_after_partial
        ):
            try:
                parse_runtime.save_cache(target, {"version": 1, "entries": {}})
            except OSError:
                pass

        self.assertIsInstance(
            json.loads(target.read_text(encoding="utf-8"))["entries"], dict
        )

    def test_replace_failure_preserves_old_json_and_cleans_temp(self) -> None:
        self.map_path.parent.mkdir(parents=True, exist_ok=True)
        old_content = '{"original":true}\n'
        self.map_path.write_text(old_content, encoding="utf-8")
        with mock.patch.object(
            cache_runtime.os, "replace", side_effect=OSError("simulated rename error")
        ):
            with self.assertRaises(OSError):
                cache_runtime.atomic_write_json(self.map_path, {"replacement": True})
        self.assertEqual(self.map_path.read_text(encoding="utf-8"), old_content)
        self.assertEqual(
            list(self.map_path.parent.glob(".project-map.json.pact-cache-*.tmp")),
            [],
        )

    def test_two_writers_one_reader_never_observe_partial_json(self) -> None:
        self.map_path.parent.mkdir(parents=True, exist_ok=True)
        target = self.map_path.parent / "concurrent-cache.json"
        parse_runtime.save_cache(target, {"version": 1, "entries": {"initial": {}}})
        original_write = pathlib.Path.write_text
        partial_started = threading.Event()
        release = threading.Event()

        def slow_non_atomic_write(path, data, *args, **kwargs):
            if path != target:
                return original_write(path, data, *args, **kwargs)
            with path.open("w", encoding="utf-8") as handle:
                handle.write('{"version":')
                handle.flush()
                partial_started.set()
                release.wait(timeout=3)
                handle.write(data[len('{"version":'):])
            return len(data)

        def read_while_writing():
            partial_started.wait(timeout=0.25)
            return json.loads(target.read_text(encoding="utf-8"))

        with mock.patch.object(
            pathlib.Path, "write_text", autospec=True,
            side_effect=slow_non_atomic_write,
        ):
            with ThreadPoolExecutor(max_workers=3) as pool:
                f1 = pool.submit(
                    parse_runtime.save_cache, target,
                    {"version": 1, "entries": {"writer-a": {"x": "A" * 256}}},
                )
                f2 = pool.submit(
                    parse_runtime.save_cache, target,
                    {"version": 1, "entries": {"writer-b": {"x": "B" * 256}}},
                )
                try:
                    seen = pool.submit(read_while_writing).result(timeout=6)
                finally:
                    release.set()
                f1.result(timeout=6)
                f2.result(timeout=6)
        self.assertEqual(seen["version"], 1)
        self.assertEqual(
            json.loads(target.read_text(encoding="utf-8"))["version"], 1
        )


if __name__ == "__main__":
    unittest.main()
