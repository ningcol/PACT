"""S2: real complete/partial Decision supersession, IDs and Markdown links.

These are entirely PACT-owned throwaway artifacts. Valid metadata and backlinks
never imply that a newer record is semantically approved by an Owner.
"""

from __future__ import annotations

import pathlib
import shutil
import sys
import tempfile
import unittest

SOURCE = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SOURCE / "scripts" / "pact"))

import check


class DecisionSupersessionLinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pact-supersession-")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        schema = self.root / ".pact" / "schema"
        schema.mkdir(parents=True)
        shutil.copy2(
            SOURCE / ".pact" / "schema" / "artifact.schema.json",
            schema / "artifact.schema.json",
        )
        self.folder = self.root / ".agents" / "decisions" / "implemented"
        self.folder.mkdir(parents=True)

    def record(self, name, ident, status, body, *, supersedes=(),
               superseded_by=None):
        path = self.folder / (name + ".md")
        front = [
            "+++", "[pact]", 'type = "decision"',
            f'id = "{ident}"', f'status = "{status}"',
            "supersedes = [" + ", ".join(f'"{item}"' for item in supersedes) + "]",
        ]
        if superseded_by:
            front.append(f'superseded_by = "{superseded_by}"')
        path.write_text("\n".join([
            *front, "+++", "", f"# Decision: {name}", "", body, "",
        ]), encoding="utf-8")
        return path

    def errors(self):
        artifacts, errors = check.discover(self.root)
        errors.extend(check.validate_artifacts(artifacts, self.root))
        errors.extend(check.validate_links(self.root))
        return artifacts, errors

    def test_full_supersession_retains_risk_and_bidirectional_history(self):
        old = self.record(
            "old-full", "DEC-OLD-FULL", "superseded",
            "Original invariant: reject unsafely shared mutable cache. "
            "Current authority: [new-full](new-full.md)",
            superseded_by="DEC-NEW-FULL",
        )
        new = self.record(
            "new-full", "DEC-NEW-FULL", "implemented",
            "Retained invariant: reject unsafely shared mutable cache. "
            "Historical reason: [old-full](old-full.md)",
            supersedes=("DEC-OLD-FULL",),
        )
        artifacts, errors = self.errors()
        self.assertEqual(errors, [], errors)
        self.assertEqual(
            {item.pact["id"] for item in artifacts},
            {"DEC-OLD-FULL", "DEC-NEW-FULL"},
        )
        self.assertIn("unsafe", new.read_text())
        self.assertIn("new-full.md", old.read_text())
        self.assertIn("old-full.md", new.read_text())

    def test_partial_supersession_retains_still_active_constraint(self):
        old = self.record(
            "old-partial", "DEC-OLD-PART", "superseded",
            "Constraint A: staged writes never replace confirmed Product Truth. "
            "Constraint B: legacy cache architecture; see [new-partial](new-partial.md).",
            superseded_by="DEC-NEW-PART",
        )
        new = self.record(
            "new-partial", "DEC-NEW-PART", "implemented",
            "Still-binding Constraint A: staged writes never replace confirmed "
            "Product Truth. Constraint B changed. "
            "Preserve [old-partial rationale](old-partial.md).",
            supersedes=("DEC-OLD-PART",),
        )
        _, errors = self.errors()
        self.assertEqual(errors, [], errors)
        self.assertIn("Still-binding Constraint A", new.read_text())
        self.assertIn("old-partial.md", new.read_text())
        self.assertIn("new-partial.md", old.read_text())

    def test_missing_old_decision_id_and_broken_history_link_fail_closed(self):
        self.record(
            "new-full", "DEC-NEW-FULL", "implemented",
            "History: [missing source](old-full.md)",
            supersedes=("DEC-OLD-FULL",),
        )
        _, errors = self.errors()
        self.assertTrue(
            any("DEC-OLD-FULL" in msg for msg in errors), errors,
        )
        self.assertTrue(
            any("old-full.md" in msg for msg in errors), errors,
        )

    def test_supersession_never_auto_archives_a_retained_constraint(self):
        self.record(
            "old-full", "DEC-OLD-FULL", "superseded",
            "Still exists with a durable rationale.",
            superseded_by="DEC-NEW-FULL",
        )
        self.record(
            "new-full", "DEC-NEW-FULL", "implemented",
            "Preserves prior rationale via [old-full](old-full.md).",
            supersedes=("DEC-OLD-FULL",),
        )
        artifacts, errors = self.errors()
        self.assertEqual(errors, [], errors)
        old = next(x for x in artifacts if x.pact["id"] == "DEC-OLD-FULL")
        self.assertEqual(old.pact["status"], "superseded")
        self.assertEqual(len(artifacts), 2)


if __name__ == "__main__":
    unittest.main()
