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

    def test_anonymous_governance_cache_cannot_override_original_policy(self) -> None:
        self.write(
            "docs/governance/approval.md",
            "# Approval policy\\n\\nNever publish without Owner approval.\\n",
        )
        original, _ = self.run_builder("map")
        source = next(d for d in original["documents"]
                      if d["path"] == "docs/governance/approval.md")
        self.assertIsNone(source["id"])
        self.assertEqual(source["artifact_type"], "document")
        forged = copy.deepcopy(original)
        for doc in forged["documents"]:
            if doc["path"] == "docs/governance/approval.md":
                doc["text"] = "Always publish automatically."
                doc["title"] = "Unrestricted approvals"
        self.map_path.write_text(json.dumps(forged) + "\\n", encoding="utf-8")
        repaired, stdout = self.run_builder("map")
        actual = next(d for d in repaired["documents"]
                      if d["path"] == "docs/governance/approval.md")
        self.assertEqual(actual, source)
        self.assertNotIn("fresh ->", stdout)

    def test_forged_anonymous_governance_parse_cache_does_not_launder(self) -> None:
        relative = "docs/product/policy.md"
        self.write(relative, "# Product approval\\n\\nNever bypass approval.\\n")
        original, _ = self.run_builder("map")
        source = next(d for d in original["documents"] if d["path"] == relative)
        cache_path = self.root / ".pact/cache/project-file-cache.json"
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        cache["entries"][relative]["parsed"]["text"] = "No owner approval required."
        cache["entries"][relative]["parsed_sha256"] = parse_runtime.parsed_digest(
            cache["entries"][relative]["parsed"]
        )
        cache_path.write_text(json.dumps(cache) + "\\n", encoding="utf-8")
        self.map_path.unlink()
        repaired, _ = self.run_builder("map")
        actual = next(d for d in repaired["documents"] if d["path"] == relative)
        self.assertEqual(actual, source)

    def test_forged_decision_cache_cannot_promote_rejected_authority(self) -> None:
        authority = self.write(
            ".agents/decisions/rejected/denied.md",
            '+++\n[pact]\ntype = "decision"\n'
            'id = "DEC-CACHE-DENIED"\nstatus = "rejected"\n'
            '+++\n# Denied authorization\n\nWe rejected this proposal.\n',
        )
        pristine, _ = self.run_builder("map")
        target = next(d for d in pristine["documents"]
                      if d.get("id") == "DEC-CACHE-DENIED")
        self.assertEqual(target["status"], "rejected")
        bad = copy.deepcopy(pristine)
        for d in bad["documents"]:
            if d.get("id") == "DEC-CACHE-DENIED":
                d["status"] = "implemented"
                d["title"] = "Approved authorization"
                d["text"] = "This is approved normative Product Truth."
        self.map_path.write_text(json.dumps(bad), encoding="utf-8")
        recovered, output = self.run_builder("map")
        repaired = next(d for d in recovered["documents"]
                        if d.get("id") == "DEC-CACHE-DENIED")
        self.assertEqual(repaired, target)
        self.assertNotIn("fresh ->", output)
        self.assertEqual(authority.read_bytes(),
                         (self.root / ".agents/decisions/rejected/denied.md").read_bytes())

    def test_forged_parse_cache_cannot_override_source_on_map_rebuild(self) -> None:
        self.write(
            ".agents/decisions/rejected/denied.md",
            '+++\n[pact]\ntype = "decision"\n'
            'id = "DEC-PARSE-DENIED"\nstatus = "rejected"\n'
            '+++\n# Denied parse-cache rule\n',
        )
        original, _ = self.run_builder("map")
        cache_path = self.root / ".pact/cache/project-file-cache.json"
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        relative = ".agents/decisions/rejected/denied.md"
        cache["entries"][relative]["parsed"]["status"] = "implemented"
        cache["entries"][relative]["parsed_sha256"] = parse_runtime.parsed_digest(
            cache["entries"][relative]["parsed"]
        )
        cache_path.write_text(json.dumps(cache), encoding="utf-8")
        # Force the map builder to consume even a validly-checksummed,
        # deliberately forged parsed result rather than trusting prior map.
        self.map_path.unlink()
        fixed, _ = self.run_builder("map")
        result = next(d for d in fixed["documents"]
                      if d.get("id") == "DEC-PARSE-DENIED")
        self.assertEqual(result["status"], "rejected")

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

    def test_code_map_schema_valid_but_missing_edges_must_rebuild(self) -> None:
        initial, _ = self.run_builder("code_map")
        self.assertTrue(initial["edges"], "fixture must have a resolved import")
        damaged = copy.deepcopy(initial)
        damaged["edges"] = []
        self.code_path.write_text(json.dumps(damaged) + "\n", encoding="utf-8")
        repaired, log = self.run_builder("code_map")
        self.assertEqual(repaired["edges"], initial["edges"])
        self.assertNotIn("fresh ->", log)

    def test_code_map_wrong_repository_root_metadata_must_rebuild(self) -> None:
        initial, _ = self.run_builder("code_map")
        damaged = copy.deepcopy(initial)
        damaged["root"] = "elsewhere"
        self.code_path.write_text(json.dumps(damaged) + "\n", encoding="utf-8")
        repaired, log = self.run_builder("code_map")
        self.assertEqual(repaired["root"], ".")
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

    def test_real_windows_sharing_conflict_classifier_is_narrow(self):
        class SimulatedWindowsPermission(PermissionError):
            def __init__(self, code):
                super().__init__(f"WinError {code} injected")
                self.winerror = code

        # Patch OS name only around the pure classifier, not around a
        # pathlib/tempfile operation (which would be nonportable on Linux).
        with mock.patch.object(cache_runtime.os, "name", "nt"):
            for code in (5, 32):
                with self.subTest(code=code):
                    self.assertTrue(
                        cache_runtime._retryable_windows_cache_replace_error(
                            SimulatedWindowsPermission(code)
                        )
                    )
            for code in (2, 13, 87):
                with self.subTest(nonretryable=code):
                    self.assertFalse(
                        cache_runtime._retryable_windows_cache_replace_error(
                            SimulatedWindowsPermission(code)
                        )
                    )
            self.assertFalse(
                cache_runtime._retryable_windows_cache_replace_error(
                    OSError("unclassified error")
                )
            )
        with mock.patch.object(cache_runtime.os, "name", "posix"):
            for code in (5, 32):
                self.assertFalse(
                    cache_runtime._retryable_windows_cache_replace_error(
                        SimulatedWindowsPermission(code)
                    )
                )

    def test_atomic_writer_uses_real_classifier_for_winerror_5_32_and_denial(self):
        class SimulatedWindowsPermission(PermissionError):
            def __init__(self, code):
                super().__init__(f"synthetic WinError {code}")
                self.winerror = code

        self.map_path.parent.mkdir(parents=True, exist_ok=True)
        initial = '{"old":true}\n'
        self.map_path.write_text(initial, encoding="utf-8")
        real_replace = cache_runtime.os.replace
        actual_classifier = cache_runtime._retryable_windows_cache_replace_error

        def call_actual_classifier(error):
            # This short scoped patch affects only the platform predicate.
            # Never alter os.name while pathlib/tempfile construct paths.
            with mock.patch.object(cache_runtime.os, "name", "nt"):
                return actual_classifier(error)

        attempts = []

        def transient_replace(source, destination):
            attempts.append(len(attempts))
            if len(attempts) in (1, 2):
                raise SimulatedWindowsPermission(5 if len(attempts) == 1 else 32)
            return real_replace(source, destination)

        with (
            mock.patch.object(
                cache_runtime,
                "_retryable_windows_cache_replace_error",
                side_effect=call_actual_classifier,
            ) as classifier,
            mock.patch.object(
                cache_runtime.os, "replace", side_effect=transient_replace,
            ),
            mock.patch.object(cache_runtime.time, "sleep"),
        ):
            cache_runtime.atomic_write_json(self.map_path, {"new": True})
        self.assertEqual(len(attempts), 3)
        self.assertEqual(classifier.call_count, 2)
        self.assertEqual(
            json.loads(self.map_path.read_text(encoding="utf-8")),
            {"new": True},
        )

        # Non-sharing WinError 87 must reach the caller on the FIRST
        # failure, keeping the previous valid complete JSON intact.
        attempts.clear()
        with (
            mock.patch.object(
                cache_runtime,
                "_retryable_windows_cache_replace_error",
                side_effect=call_actual_classifier,
            ) as classifier,
            mock.patch.object(
                cache_runtime.os, "replace",
                side_effect=SimulatedWindowsPermission(87),
            ) as replaced,
            mock.patch.object(cache_runtime.time, "sleep") as sleep,
        ):
            with self.assertRaises(SimulatedWindowsPermission):
                cache_runtime.atomic_write_json(self.map_path, {"bad": True})
        classifier.assert_called_once()
        replaced.assert_called_once()
        sleep.assert_not_called()
        self.assertEqual(
            json.loads(self.map_path.read_text(encoding="utf-8")),
            {"new": True},
        )
        self.assertEqual(
            list(self.map_path.parent.glob(".project-map.json.pact-cache-*.tmp")),
            [],
        )

    def test_transient_windows_replace_conflict_retries_without_partial_json(self):
        self.map_path.parent.mkdir(parents=True, exist_ok=True)
        self.map_path.write_text('{"old":true}\n', encoding="utf-8")
        original_replace = cache_runtime.os.replace
        calls = []

        def transient(source, target):
            calls.append((source, target))
            if len(calls) <= 2:
                raise PermissionError("simulated transient Windows sharing lock")
            return original_replace(source, target)

        with (
            mock.patch.object(
                cache_runtime,
                "_retryable_windows_cache_replace_error",
                return_value=True,
            ),
            mock.patch.object(cache_runtime.os, "replace", side_effect=transient),
            mock.patch.object(cache_runtime.time, "sleep"),
        ):
            cache_runtime.atomic_write_json(self.map_path, {"new": True})

        self.assertEqual(len(calls), 3)
        self.assertEqual(
            json.loads(self.map_path.read_text(encoding="utf-8")), {"new": True}
        )
        self.assertEqual(
            list(self.map_path.parent.glob(".project-map.json.pact-cache-*.tmp")),
            [],
        )

    def test_permanent_windows_sharing_denial_stays_bounded_and_fail_closed(self):
        self.map_path.parent.mkdir(parents=True, exist_ok=True)
        prior = '{"old":true}\n'
        self.map_path.write_text(prior, encoding="utf-8")
        with (
            mock.patch.object(
                cache_runtime,
                "_retryable_windows_cache_replace_error",
                return_value=True,
            ),
            mock.patch.object(
                cache_runtime.os, "replace",
                side_effect=PermissionError("persistent Windows sharing lock"),
            ) as replaced,
            mock.patch.object(cache_runtime.time, "sleep") as sleep,
        ):
            with self.assertRaises(PermissionError):
                cache_runtime.atomic_write_json(self.map_path, {"new": True})

        self.assertEqual(
            replaced.call_count, cache_runtime.WINDOWS_CACHE_REPLACE_MAX_ATTEMPTS
        )
        self.assertEqual(sleep.call_count, replaced.call_count - 1)
        self.assertEqual(self.map_path.read_text(encoding="utf-8"), prior)
        self.assertEqual(
            list(self.map_path.parent.glob(".project-map.json.pact-cache-*.tmp")),
            [],
        )

    def test_non_retryable_permission_error_fails_without_retry(self):
        self.map_path.parent.mkdir(parents=True, exist_ok=True)
        self.map_path.write_text('{"old":true}\n', encoding="utf-8")
        with (
            mock.patch.object(
                cache_runtime,
                "_retryable_windows_cache_replace_error",
                return_value=False,
            ),
            mock.patch.object(
                cache_runtime.os, "replace",
                side_effect=PermissionError("actual permission denial"),
            ) as replaced,
            mock.patch.object(cache_runtime.time, "sleep") as sleep,
        ):
            with self.assertRaises(PermissionError):
                cache_runtime.atomic_write_json(self.map_path, {"new": True})
        replaced.assert_called_once()
        sleep.assert_not_called()
        self.assertEqual(
            json.loads(self.map_path.read_text(encoding="utf-8")), {"old": True}
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

    def test_missing_snapshot_source_never_silently_hashes_to_success(self) -> None:
        vanished = self.root / "docs" / "vanished.md"
        with self.assertRaises(OSError):
            cache_runtime.fingerprint_files(self.root, [vanished])

    def test_transient_parse_failure_retries_without_partial_index(self) -> None:
        real_parse = project_map.parse_with_cache
        attempts = 0

        def transient(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise FileNotFoundError("transient disappearing source")
            return real_parse(*args, **kwargs)

        with mock.patch.object(project_map, "parse_with_cache", side_effect=transient):
            self.assertEqual(self.run_in_process("map"), 0)
        self.assertEqual(attempts, 2)
        indexed = json.loads(self.map_path.read_text(encoding="utf-8"))
        self.assertIn("README.md", [doc["path"] for doc in indexed["documents"]])

    def test_permanent_source_failure_does_not_publish_map(self) -> None:
        original, _ = self.run_builder("map")
        self.write("docs/guide.md", "# Changed while scanning\n")
        with mock.patch.object(
            project_map,
            "parse_with_cache",
            side_effect=FileNotFoundError("permanent missing source"),
        ):
            self.assertEqual(self.run_in_process("map"), 2)
        self.assertEqual(
            json.loads(self.map_path.read_text(encoding="utf-8")),
            original,
        )

    def test_parse_cache_rejects_disappeared_file(self) -> None:
        missing = self.root / "docs" / "missing.md"
        with self.assertRaises(OSError):
            parse_runtime.parse_with_cache(
                root=self.root,
                paths=[missing],
                cache_path=self.root / ".pact" / "cache" / "test-missing.json",
                cache_version=1,
                parser=lambda path: path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
