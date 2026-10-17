"""M0: deterministic Decision relationship integrity, with no Agent/Owner claims.

The tests use only disposable PACT-owned files. They exercise repository
metadata/index boundaries, not semantic validity or automatic approval.
"""
from __future__ import annotations

import copy
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "pact"))

import check
import map as project_map


class DecisionMemoryIndexIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pact-m0-decision-")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        schema = self.root / ".pact" / "schema"
        schema.mkdir(parents=True)
        shutil.copy2(
            ROOT / ".pact" / "schema" / "artifact.schema.json",
            schema / "artifact.schema.json",
        )
        self.folder = self.root / ".agents" / "decisions" / "implemented"
        self.folder.mkdir(parents=True)

    def record(
        self, name: str, ident: str, *, supersedes: tuple[str, ...] = (),
        superseded_by: str | None = None, status: str = "implemented",
    ) -> pathlib.Path:
        lines = [
            "+++", "[pact]", 'type = "decision"',
            f'id = "{ident}"', f'status = "{status}"',
            "supersedes = [" + ", ".join(f'"{id_}"' for id_ in supersedes) + "]",
            'paths = ["src/auth/"]',
        ]
        if superseded_by:
            lines.append(f'superseded_by = "{superseded_by}"')
        path = self.folder / f"{name}.md"
        path.write_text(
            "\n".join([*lines, "+++", "", f"# Decision: {name}", "",
                       "Important original rationale retained.", ""]),
            encoding="utf-8",
        )
        return path

    def test_project_index_retains_existing_supersession_metadata(self) -> None:
        path = self.record(
            "middle", "DEC-MIDDLE", supersedes=("DEC-OLD",),
            superseded_by="DEC-NEW", status="superseded",
        )
        parsed = project_map.parse_document(path, self.root)
        self.assertEqual(parsed["supersedes"], ["DEC-OLD"])
        self.assertEqual(parsed["superseded_by"], "DEC-NEW")
        index = project_map.build_index(
            self.root, [parsed], "fixed-fixture-sha",
            enumeration_mode="filesystem",
        )
        self.assertEqual(index["documents"][0]["supersedes"], ["DEC-OLD"])
        self.assertEqual(index["documents"][0]["superseded_by"], "DEC-NEW")
        self.assertTrue(project_map.valid_project_index(
            index, expected_paths={parsed["path"]},
        ))
        # A structurally incomplete old map must not shadow repository truth,
        # even when its source fingerprint and file inventory are unchanged.
        incomplete = copy.deepcopy(index)
        del incomplete["documents"][0]["supersedes"]
        self.assertFalse(project_map.valid_project_index(
            incomplete, expected_paths={parsed["path"]},
        ))

    def test_cyclic_supersession_ids_do_not_pass_deterministic_check(self) -> None:
        self.record("a", "DEC-A", supersedes=("DEC-B",))
        self.record("b", "DEC-B", supersedes=("DEC-A",))
        artifacts, errors = check.discover(self.root)
        self.assertEqual(errors, [])
        result = check.validate_artifacts(artifacts, self.root)
        self.assertTrue(
            any("cycle" in message.lower() for message in result),
            "a fully present, valid-ID supersession cycle must not be "
            f"accepted as a historical lineage: {result!r}",
        )

    def test_one_way_supersession_is_legacy_compatible(self) -> None:
        self.record("old", "DEC-OLD", status="superseded")
        self.record("new", "DEC-NEW", supersedes=("DEC-OLD",))
        artifacts, errors = check.discover(self.root)
        self.assertEqual(errors, [])
        self.assertEqual(check.validate_artifacts(artifacts, self.root), [])


if __name__ == "__main__":
    unittest.main()
