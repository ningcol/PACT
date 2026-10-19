"""Frozen second real-repository benchmark: integrity before subjective metrics."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))
import privacyfence_pilot as pilot


class PinnedPrivacyFenceTests(unittest.TestCase):
    def test_case_oracle_precommitted_source_sha(self):
        self.assertEqual(pilot.pilot.git_blob_sha(pilot.CASES), pilot.CASES_BLOB)
        self.assertEqual(pilot.pilot.git_blob_sha(pilot.ORACLE), pilot.ORACLE_BLOB)
        cards = json.loads(pilot.CASES.read_text(encoding="utf-8"))
        oracle = json.loads(pilot.ORACLE.read_text(encoding="utf-8"))
        self.assertEqual(cards["upstream_commit"], pilot.UPSTREAM_SHA)
        self.assertEqual(cards["pact_baseline"], pilot.PACT_BASE)
        self.assertEqual(len(cards["source_docs"]), 12)
        self.assertEqual(len(cards["tasks"]), 12)
        self.assertEqual(sum(d["status"] == "proposed"
                             for d in cards["source_docs"]), 1)
        self.assertEqual(sum(t["kind"] == "conflict" for t in cards["tasks"]), 10)
        self.assertEqual(sum(t["kind"] == "routine-negative" for t in cards["tasks"]), 2)
        self.assertEqual(set(oracle["expected_current"]),
                         {t["id"] for t in cards["tasks"]})
        for case in cards["tasks"]:
            self.assertNotIn("DEC-PF-", case["task"])
            self.assertNotIn("docs/adr/", case["task"])

    def test_relative_source_links_keep_original_meaning(self):
        text = (
            "# Original ADR\n"
            "Use [peer decision](0008-one-principal-per-os-user.md), "
            "[policy](../policy/README.md#topic), "
            "[web](https://example.org/a), [local](#part).\n"
        )
        modified = pilot.rebase_links(
            text, "docs/adr/0011-org-mode.md",
            ".agents/decisions/implemented/dec-pf-0011.md",
        )
        self.assertIn("../../../docs/adr/0008-one-principal-per-os-user.md", modified)
        self.assertIn("../../../docs/policy/README.md#topic", modified)
        self.assertIn("(https://example.org/a)", modified)
        self.assertIn("(#part)", modified)
        self.assertEqual(modified.count("# Original ADR"), 1)
        self.assertEqual(modified.count("peer decision"), 1)

    def test_source_metadata_is_status_faithful_and_minimal(self):
        with tempfile.TemporaryDirectory(prefix="pact-pf-fixture-") as td:
            root = pathlib.Path(td)
            docs = [
                {"id":"DEC-PF-0005", "source":"docs/adr/0005-sample.md",
                 "status":"proposed"},
                {"id":"DEC-PF-0013", "source":"docs/adr/0013-sample.md",
                 "status":"implemented"},
            ]
            for d in docs:
                path = root / d["source"]
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(
                    f"# Decision {d['id']}\n\n## Status\n\n"
                    + ("Proposed" if d["status"]=="proposed" else "Accepted")
                    + "\n\n## Decision\nKeep the source constraint.\n",
                    encoding="utf-8",
                )
            paths = pilot.project_sources(root,{"source_docs":docs})
            self.assertEqual(len(paths),2)
            for d in docs:
                relative = pilot.target_path(d)
                result = (root / relative).read_text(encoding="utf-8")
                self.assertIn('id = "'+d["id"]+'"',result)
                self.assertIn('status = "'+d["status"]+'"',result)
                self.assertIn("aliases = []",result)
                self.assertIn("domains = []",result)
                self.assertIn("paths = []",result)
                self.assertIn("Keep the source constraint.",result)
                self.assertEqual(paths[relative],pilot.m0.digest_file(root/relative))
                self.assertTrue((root/d["source"]).is_file())

    def test_unsupported_original_external_link_rejected(self):
        with self.assertRaisesRegex(ValueError,"exits upstream checkout"):
            pilot.rebase_links(
                "# Demo\n[unsafe](../../../external.md)",
                "docs/adr/original.md", ".agents/decisions/implemented/dec-pf-0001.md",
            )

    def test_missing_real_checkout_does_not_fake_success(self):
        with tempfile.TemporaryDirectory() as td:
            result=pilot.trial(pathlib.Path(td))
        self.assertEqual(result["engineering_gate"],"FAIL")
        self.assertEqual(result["release_gate"],"HOLD")
        self.assertFalse(result["real_agent_executed"])
        self.assertFalse(result["independent_holdout"])
        self.assertFalse(result["owner_approval_authenticated"])
        self.assertTrue(result["integrity_failures"])

    def test_source_target_path_does_not_allow_status_promotion(self):
        self.assertIn("/proposed/",
                      pilot.target_path({"id":"DEC-PF-0005","status":"proposed"}))
        self.assertIn("/implemented/",
                      pilot.target_path({"id":"DEC-PF-0013","status":"implemented"}))



    def test_malformed_successful_discover_is_an_integrity_failure(self):
        with tempfile.TemporaryDirectory() as td:
            target=pathlib.Path(td)
            cards={"settings":{
                "risk":"low","intent":"work","knowledge_limit":6,
                "estimated_token_budget":4096,"code_context":False,
            },"source_docs":[],"tasks":[{
                "id":"noise-negative","kind":"routine-negative",
                "task":"Correct a comment in a test",
            }]}
            def receipt(data,command):
                return {"returncode":0,"data":data,"command":["pact.py",command],
                        "stderr":"","elapsed_ms":1}
            with mock.patch.object(pilot.m0,"run_json",side_effect=[
                receipt({"results":{}},"discover"),
                receipt({"artifacts":[],"decisions":[]},"context"),
            ]):
                results=pilot.run_arm(target,cards,"B")
        self.assertEqual(len(results),1)
        self.assertTrue(any("missing/non-array results" in msg
                            for msg in results[0]["schema_and_source_errors"]))
        self.assertEqual(results[0]["source_verified_decisions"], [])

    def test_claimed_id_without_selected_source_is_not_scored_as_recall(self):
        with tempfile.TemporaryDirectory() as td:
            target=pathlib.Path(td)
            cards={"settings":{
                "risk":"low","intent":"work","knowledge_limit":6,
                "estimated_token_budget":4096,"code_context":False,
            },"source_docs":[{
                "id":"DEC-PF-0008","status":"implemented",
                "source":"docs/adr/0008-sample.md",
            }],"tasks":[{
                "id":"os-principal","kind":"conflict",
                "task":"Change the account model",
            }]}
            def receipt(data,command):
                return {"returncode":0,"data":data,"command":["pact.py",command],
                        "stderr":"","elapsed_ms":1}
            with mock.patch.object(pilot.m0,"run_json",side_effect=[
                receipt({"results":[]},"discover"),
                receipt({"artifacts":[],"decisions":["DEC-PF-0008"]},"context"),
            ]):
                results=pilot.run_arm(target,cards,"B")
        errors=results[0]["schema_and_source_errors"]
        self.assertTrue(any("lacks a matching selected" in msg for msg in errors),
                        errors)
        self.assertEqual(results[0]["source_verified_decisions"], [])
        self.assertEqual(results[0]["decisions"], ["DEC-PF-0008"])

    def test_developer_recall_counts_only_source_verified_ids(self):
        cards=json.loads(pilot.CASES.read_text(encoding="utf-8"))
        oracle=json.loads(pilot.ORACLE.read_text(encoding="utf-8"))
        a=[];b=[]
        for case in cards["tasks"]:
            common={
                "id":case["id"],"kind":case["kind"],"selected":[],
                "budget":{"selected_estimated_tokens":1},
                "context_ms":1,"decisions":[],
                "source_verified_decisions":[],
            }
            a.append(dict(common))
            row=dict(common)
            # Fabricated Context claims MUST NOT count as success.
            row["decisions"]=list(oracle["expected_current"][case["id"]])
            b.append(row)
        score=pilot.score({"arms":{
            "A_unadapted":a,"B_source_projection":b,
        }},cards)
        self.assertEqual(score["developer_target_count"],10)
        self.assertEqual(score["B_current_decision_target_hits"],0)
        self.assertEqual(score["B_extra_current_decision_slots"],0)
        self.assertTrue(all(
            case["target_hit"] is False for case in score["per_case"]
        ))



    def test_real_context_omits_status_but_source_verified_id_counts(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            docs=[{"id":"DEC-PF-0008","status":"implemented",
                   "source":"docs/adr/0008-sample.md"}]
            source_path=pilot.target_path(docs[0])
            file=root/source_path
            file.parent.mkdir(parents=True,exist_ok=True)
            file.write_text(
                '+++\n[pact]\ntype = "decision"\nid = "DEC-PF-0008"\n'
                'status = "implemented"\n+++\n# Source-backed decision\n',
                encoding="utf-8",
            )
            cards={
                "settings":{"risk":"low","intent":"work","knowledge_limit":6,
                           "estimated_token_budget":4096,"code_context":False},
                "source_docs":docs,
                "tasks":[{"id":"os-principal","kind":"conflict",
                          "task":"Change the account model"}],
            }
            result = {
                "id":"DEC-PF-0008","artifact_type":"decision",
                "status":"implemented","path":source_path,
            }
            selected = {
                "id":"DEC-PF-0008","artifact_type":"decision",
                "path":source_path,"sha256":pilot.m0.digest_file(file),
                # Context schema intentionally does NOT include 'status'.
            }
            def receipt(data,command):
                return {"returncode":0,"data":data,"command":["pact.py",command],
                        "stderr":"","elapsed_ms":1}
            with mock.patch.object(pilot.m0,"run_json",side_effect=[
                receipt({"results":[result]},"discover"),
                receipt({"artifacts":[selected],
                         "decisions":["DEC-PF-0008"],
                         "applicable_rules":[]},"context"),
            ]), mock.patch.object(pilot,"validate_instance",return_value=[]):
                records=pilot.run_arm(root,cards,"B")
        self.assertEqual(records[0]["schema_and_source_errors"],[])
        self.assertEqual(records[0]["source_verified_decisions"],
                         ["DEC-PF-0008"])
        self.assertIsNone(records[0]["selected"][0]["reported_status"])
        self.assertEqual(records[0]["selected"][0]["source_expected_status"],
                         "implemented")



    def test_proposed_status_guard_rejects_bare_success_payload(self):
        with tempfile.TemporaryDirectory() as td:
            packet = pilot.inspect_proposed_context(
                pathlib.Path(td), {"source_docs":[]},
                {"returncode":0,"stderr":"","data":{"decisions":[]}},
            )
        self.assertEqual(packet["decisions"], [])
        self.assertTrue(packet["schema_and_source_errors"],
                        "A bare Decision list is not a complete Context envelope")
        self.assertTrue(any(
            "missing selected artifact" in error
            for error in packet["schema_and_source_errors"]
        ))

    def test_proposed_status_guard_binds_sources_even_if_shape_valid(self):
        with tempfile.TemporaryDirectory(prefix="pact-pf-guard-") as td:
            target=pathlib.Path(td)
            docs=[{"id":"DEC-PF-0005",
                   "source":"docs/adr/0005-original.md","status":"proposed"}]
            relative=pilot.target_path(docs[0])
            p=target/relative
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                '+++\n[pact]\ntype = "decision"\nid = "DEC-PF-0005"\n'
                'status = "proposed"\n+++\n# Original Proposed source\n',
                encoding="utf-8",
            )
            item={"id":"DEC-PF-0005","path":relative,
                  "artifact_type":"decision",
                  "sha256":pilot.m0.digest_file(p)}
            def lookup(selected):
                return {"returncode":0,"stderr":"",
                        "data":{"decisions":[],"artifacts":selected}}
            with mock.patch.object(pilot,"validate_instance",return_value=[]):
                valid=pilot.inspect_proposed_context(
                    target,{"source_docs":docs},lookup([item]),
                )
                empty=pilot.inspect_proposed_context(
                    target,{"source_docs":docs},lookup([]),
                )
                tampered=pilot.inspect_proposed_context(
                    target,{"source_docs":docs},
                    lookup([{**item,"sha256":"0"*64}]),
                )
                forged=pilot.inspect_proposed_context(
                    target,{"source_docs":docs},
                    lookup([{**item,"path":"docs/adr/0005-original.md",
                             "sha256":"0"*64}]),
                )
                promoted=pilot.inspect_proposed_context(
                    target,{"source_docs":docs},
                    {"returncode":0,"stderr":"",
                     "data":{"decisions":["DEC-PF-0005"],"artifacts":[item]}},
                )
        self.assertEqual(valid["schema_and_source_errors"], [])
        self.assertTrue(any(
            "did not materialize" in e
            for e in empty["schema_and_source_errors"]
        ), "a schema-valid but empty Context must not falsely certify Proposed")
        self.assertTrue(any("digest invalid" in e
                            for e in tampered["schema_and_source_errors"]))
        self.assertTrue(forged["schema_and_source_errors"])
        self.assertTrue(any("promoted" in e
                            for e in promoted["schema_and_source_errors"]))



    def test_arm_retains_completed_case_when_later_discover_times_out(self):
        cards = {
            "settings":{"risk":"low","intent":"work","knowledge_limit":6,
                        "estimated_token_budget":4096,"code_context":False},
            "source_docs":[],
            "tasks":[
                {"id":"first","kind":"routine-negative","task":"Fix whitespace"},
                {"id":"second","kind":"conflict","task":"Change a decision"},
            ],
        }
        def receipt(data,command):
            return {"returncode":0,"data":data,"command":["pact.py",command],
                    "stderr":"","elapsed_ms":1}
        with tempfile.TemporaryDirectory() as td:
            output=[]
            in_flight={}
            with mock.patch.object(pilot.m0,"run_json",side_effect=[
                receipt({"results":[]},"discover"),
                receipt({"artifacts":[],"decisions":[]},"context"),
                subprocess.TimeoutExpired(
                    cmd=["pact.py","discover","Change a decision"],timeout=90,
                ),
            ]):
                with self.assertRaises(subprocess.TimeoutExpired):
                    pilot.run_arm(
                        pathlib.Path(td),cards,"B",
                        result=output,in_flight=in_flight,
                    )
        self.assertEqual([x["id"] for x in output],["first"])
        self.assertEqual(in_flight["id"],"second")
        self.assertEqual(in_flight["stage"],"discover")
        self.assertEqual(in_flight["arm"],"B")
        self.assertEqual(in_flight["command"][0:2],["pact.py","discover"])

    def test_trial_preserves_partial_results_and_failing_command(self):
        def fail_late(target,cards,label,*,result,in_flight):
            result.append({"id":"first","kind":"routine-negative",
                           "schema_and_source_errors":[]})
            in_flight.update({"arm":label,"id":"second","stage":"context",
                              "command":["pact.py","context","Change a decision"]})
            raise subprocess.TimeoutExpired(
                cmd=["python","pact.py","context","Change a decision"],
                timeout=90,
            )
        with tempfile.TemporaryDirectory() as td, \
                mock.patch.object(pilot,"verify_freeze",return_value={}), \
                mock.patch.object(pilot.pilot,"install_pact",return_value={}), \
                mock.patch.object(pilot,"run_arm",side_effect=fail_late):
            result=pilot.trial(pathlib.Path(td))
        self.assertEqual(result["engineering_gate"],"FAIL")
        self.assertEqual(result["release_gate"],"HOLD")
        self.assertEqual(result["stage"],"A-unadapted-source")
        self.assertEqual([x["id"] for x in result["arms"]["A_unadapted"]],
                         ["first"])
        self.assertEqual(result["in_flight_probe"]["id"],"second")
        self.assertEqual(result["in_flight_probe"]["stage"],"context")
        self.assertEqual(result["timed_out_command"][:3],
                         ["python","pact.py","context"])
        self.assertTrue(any("TimeoutExpired" in e
                            for e in result["integrity_failures"]))


if __name__ == "__main__":
    unittest.main()
