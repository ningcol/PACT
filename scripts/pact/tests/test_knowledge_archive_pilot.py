"""Safety boundaries of the fixed, no-commit real-source rehearsal."""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))
import knowledge_archive_pilot as pilot


class KnowledgeArchivePilotTests(unittest.TestCase):
    def test_interrupted_output_is_preserved_without_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = pathlib.Path(tmp) / "interrupted"
            output.mkdir()
            marker = output / "owner-notes.txt"
            marker.write_text("preserve interrupted review")
            with patch.object(pilot.Meter, "run", side_effect=AssertionError("must not run Git")):
                with self.assertRaises(FileExistsError):
                    pilot.run(pathlib.Path(tmp) / "source", output, "unselected", None, upgrade=False)
            self.assertEqual(marker.read_text(), "preserve interrupted review")

    def test_fixed_mapping_preserves_prose_and_fragment_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve()
            source = root / pilot.SOURCE_REL
            source.parent.mkdir(parents=True)
            original_target = source.parent.parent / "reference.md"
            original_target.write_text('# Reference\n\n<a id="scope"></a>\n')
            text = "# Ordinary explanation\n\n[Reference](../reference.md#scope)\n"
            mapped, links = pilot.rebase_links(text, root)
            self.assertEqual(pilot.without_destinations(text), pilot.without_destinations(mapped))
            self.assertEqual(links[0]["fragment"], "scope")
            self.assertEqual(
                ((root / pilot.TARGET_REL).parent / links[0]["new"].split("#")[0]).resolve(),
                original_target.resolve(),
            )

    def test_unknown_link_shape_requires_manual_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                pilot.rebase_links("[Reference](<a path.md>)", pathlib.Path(tmp))

    def test_upgrade_snapshot_includes_knowledge_below_parent_pact_tmp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / ".pact/tmp/clone"
            business = root / pilot.TARGET_REL
            business.parent.mkdir(parents=True)
            business.write_text("# Project-owned explanation\n")
            managed = root / ".pact/runtime-note.md"
            managed.parent.mkdir()
            managed.write_text("framework state")
            snapshot = pilot.project_markdown_snapshot(root)
            self.assertEqual(set(snapshot), {pilot.TARGET_REL})

    def test_integrated_review_preserves_scope_and_rejects_stale_alignment(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = pilot.fixture_rehearsal(pathlib.Path(tmp) / "fixture")
            self.assertTrue(result["integrated_distinct_id_paraphrase_hint"])
            self.assertTrue(result["same_title_different_scope_hint_without_merge"])
            self.assertTrue(result["all_candidate_statuses_preserved"])
            self.assertTrue(result["stale_aligned_rejected"])

    def test_manual_procedure_keeps_whole_sources_and_one_shared_open_dispute(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve()
            meter = pilot.Meter()
            missing = subprocess.CompletedProcess([], 1, b"", b"missing Git object")
            with patch.object(meter, "run", return_value=missing) as command:
                result = pilot.manual_procedure_fixture(root / "held", root / "clone", meter)
            self.assertEqual(command.call_count, 1)
            self.assertEqual(result["shared_disputes"], 1)
            self.assertTrue(result["source_bytes_unchanged"])
            self.assertTrue(result["closure_rejected"])
            self.assertTrue(result["unversioned_retirement_deferred"])
            self.assertEqual(len(list((root / "held/docs/drift").rglob("*.md"))), 1)


if __name__ == "__main__":
    unittest.main()
