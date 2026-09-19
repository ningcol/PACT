from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import unittest
import zipfile


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
BOOTSTRAP = PROJECT_ROOT / "bootstrap.py"

spec = importlib.util.spec_from_file_location("pact_bootstrap_module", BOOTSTRAP)
bootstrap = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(bootstrap)


class BootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-bootstrap-test-")
        self.root = pathlib.Path(self.temp.name)
        self.target = self.root / "target"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def make_fake_archive(self) -> pathlib.Path:
        source_root = self.root / "fake-source" / "fake-root"
        runtime = source_root / "scripts" / "pact" / "pact.py"
        runtime.parent.mkdir(parents=True, exist_ok=True)
        runtime.write_text(
            """
import pathlib
import sys

command = sys.argv[1]
target = pathlib.Path(sys.argv[sys.argv.index("--target") + 1])
target.mkdir(parents=True, exist_ok=True)
(target / f"{command}.marker").write_text(" ".join(sys.argv[1:]), encoding="utf-8")
raise SystemExit(0)
""".lstrip(),
            encoding="utf-8",
        )

        archive = self.root / "fake-pact.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            for path in source_root.rglob("*"):
                if path.is_file():
                    arcname = path.relative_to(source_root.parent).as_posix()
                    zf.write(path, arcname)
        return archive

    def run_bootstrap(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(BOOTSTRAP), *args],
            capture_output=True,
            text=True,
        )

    def test_local_archive_init_invokes_downloaded_runtime(self) -> None:
        archive = self.make_fake_archive()
        result = self.run_bootstrap(
            "init",
            "--target",
            str(self.target),
            "--archive",
            str(archive),
            "--ref",
            "test-ref",
            "--apply",
            "--github-actions",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        marker = (self.target / "init.marker").read_text(encoding="utf-8")
        self.assertIn("init", marker)
        self.assertIn("--apply", marker)
        self.assertIn("--github-actions", marker)

    def test_local_archive_upgrade_passes_extracted_source(self) -> None:
        archive = self.make_fake_archive()
        result = self.run_bootstrap(
            "upgrade",
            "--target",
            str(self.target),
            "--archive",
            str(archive),
            "--ref",
            "test-ref",
            "--apply",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        marker = (self.target / "upgrade.marker").read_text(encoding="utf-8")
        self.assertIn("upgrade", marker)
        self.assertIn("--source", marker)
        self.assertIn("--apply", marker)

    def test_sha256_mismatch_is_rejected(self) -> None:
        archive = self.make_fake_archive()
        result = self.run_bootstrap(
            "init",
            "--target",
            str(self.target),
            "--archive",
            str(archive),
            "--ref",
            "test-ref",
            "--sha256",
            "0" * 64,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("SHA256 mismatch", result.stderr)

    def test_matching_sha256_is_accepted(self) -> None:
        archive = self.make_fake_archive()
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        result = self.run_bootstrap(
            "init",
            "--target",
            str(self.target),
            "--archive",
            str(archive),
            "--ref",
            "test-ref",
            "--sha256",
            digest,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_local_archive_size_limit_is_enforced(self) -> None:
        source = self.root / "oversized.zip"
        source.write_bytes(b"xx")
        destination = self.root / "copy.zip"

        original = bootstrap.MAX_ARCHIVE_BYTES
        bootstrap.MAX_ARCHIVE_BYTES = 1
        try:
            with self.assertRaisesRegex(RuntimeError, "exceeds"):
                bootstrap.download_archive(
                    "ignored/repo",
                    "ignored-ref",
                    destination,
                    archive_override=source,
                )
        finally:
            bootstrap.MAX_ARCHIVE_BYTES = original

    def test_archive_entry_count_limit_is_enforced_before_extract(self) -> None:
        archive = self.root / "many.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("root/a.txt", "a")
            zf.writestr("root/b.txt", "b")
            zf.writestr("root/c.txt", "c")

        original = bootstrap.MAX_ARCHIVE_ENTRIES
        bootstrap.MAX_ARCHIVE_ENTRIES = 2
        try:
            with self.assertRaisesRegex(RuntimeError, "too many files"):
                bootstrap.safe_extract(archive, self.root / "extract-many")
        finally:
            bootstrap.MAX_ARCHIVE_ENTRIES = original

    def test_archive_uncompressed_limits_are_enforced_before_extract(self) -> None:
        single = self.root / "single-large.zip"
        with zipfile.ZipFile(single, "w") as zf:
            zf.writestr("root/large.txt", "123456")

        original_file = bootstrap.MAX_UNCOMPRESSED_FILE_BYTES
        bootstrap.MAX_UNCOMPRESSED_FILE_BYTES = 5
        try:
            with self.assertRaisesRegex(RuntimeError, "too large"):
                bootstrap.safe_extract(single, self.root / "extract-single")
        finally:
            bootstrap.MAX_UNCOMPRESSED_FILE_BYTES = original_file

        total = self.root / "total-large.zip"
        with zipfile.ZipFile(total, "w") as zf:
            zf.writestr("root/a.txt", "123456")
            zf.writestr("root/b.txt", "abcdef")

        original_total = bootstrap.MAX_UNCOMPRESSED_BYTES
        bootstrap.MAX_UNCOMPRESSED_BYTES = 10
        try:
            with self.assertRaisesRegex(RuntimeError, "allowed total size"):
                bootstrap.safe_extract(total, self.root / "extract-total")
        finally:
            bootstrap.MAX_UNCOMPRESSED_BYTES = original_total

    def test_suspicious_compression_ratio_is_rejected(self) -> None:
        archive = self.root / "ratio.zip"
        with zipfile.ZipFile(
            archive,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as zf:
            zf.writestr("root/repeated.bin", b"A" * (1024 * 1024))

        original = bootstrap.MAX_COMPRESSION_RATIO
        bootstrap.MAX_COMPRESSION_RATIO = 2
        try:
            with self.assertRaisesRegex(RuntimeError, "compression ratio"):
                bootstrap.safe_extract(archive, self.root / "extract-ratio")
        finally:
            bootstrap.MAX_COMPRESSION_RATIO = original

    def test_zip_slip_archive_is_rejected(self) -> None:
        archive = self.root / "unsafe.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("../escape.txt", "bad")

        result = self.run_bootstrap(
            "init",
            "--target",
            str(self.target),
            "--archive",
            str(archive),
            "--ref",
            "test-ref",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unsafe archive path", result.stderr)
        self.assertFalse((self.root / "escape.txt").exists())


if __name__ == "__main__":
    unittest.main()
