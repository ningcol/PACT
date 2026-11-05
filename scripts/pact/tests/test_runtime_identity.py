"""Runtime identity is sampled integrity, not a business verification badge."""
import hashlib
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from runtime_identity import runtime_identity


class RuntimeIdentityTests(unittest.TestCase):
    def test_same_version_different_archive_is_visible_and_manifest_is_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            state = root / ".pact"
            state.mkdir()
            (state / "VERSION").write_text("same-version")
            bundle = state / "pact.pyz"
            bundle.write_bytes(b"original")
            digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
            (state / "install.json").write_text(json.dumps({
                "format_version": 1, "runtime_version": "same-version", "files": {
                    ".pact/pact.pyz": {"management": "framework", "installed_sha256": digest,
                                       "source_path": ".pact/pact.pyz", "source_sha256": digest}}}))
            first = runtime_identity(root)
            self.assertEqual(first["integrity"], "matched")
            bundle.write_bytes(b"different")
            second = runtime_identity(root)
            self.assertEqual(second["version"], first["version"])
            self.assertNotEqual(second["sha256"], first["sha256"])
            self.assertEqual(second["integrity"], "mismatch")

    def test_source_and_unsafe_runtime_are_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / ".pact").mkdir()
            self.assertEqual(runtime_identity(root)["integrity"], "source")
            (root / ".pact/pact.pyz").mkdir()
            # A directory must not become an archive digest or trusted identity.
            self.assertIsNone(runtime_identity(root)["sha256"])
            self.assertEqual(runtime_identity(root)["integrity"], "error")
