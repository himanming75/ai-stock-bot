import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.paper_operator_decision_recorder_v75_2e import (
    PaperOperatorDecisionError, build_decision_record, canonical_json,
    deterministic_decision_id, main, sha256_of
)


def with_hash(obj, field):
    obj = copy.deepcopy(obj)
    obj[field] = sha256_of(obj)
    return obj


def review_fixture():
    checklist = [{"review_index": i, "review_item": f"ITEM_{i}", "state": "PENDING_OPERATOR_CONFIRMATION", "operator_confirmed": False} for i in range(1, 6)]
    review = {
        "status": "PASS", "decision": "paper_operator_review_package_created",
        "review_state": "AWAITING_OPERATOR_DECISION", "review_id": "POR-0123456789ABCDEF",
        "preflight_id": "PDP-0123456789ABCDEF", "bundle_id": "PDB-0123456789ABCDEF",
        "session_id": "PAPER-0123456789ABCDEF", "champion_candidate_id": "CAND-A",
        "review_checklist": checklist,
        "operator_decision": {"decision_state": "PENDING", "selected_decision": None, "allowed_decisions": ["APPROVE_PAPER", "REJECT", "HOLD"], "decision_recorded": False},
        "activation_gate": {"activation_allowed": False, "next_version": "75.2E", "operator_decision_recorded": False, "operator_signature_verified": False},
        "safety_lock": {"network_enabled": False, "live_orders_enabled": False, "broker_credentials_required": False, "external_side_effects_allowed": False, "automatic_approval_allowed": False, "lock_state": "ENFORCED"},
        "approved_for_live": False, "network_used": False,
        "schema_version": "v75.2d.paper_operator_review_package.1", "version": "75.2D",
    }
    return with_hash(review, "paper_operator_review_package_sha256")


def config_fixture():
    return {"allowed_operator_decisions": ["APPROVE_PAPER", "REJECT", "HOLD"], "operator_name_required": True, "operator_signature_required": True, "decision_reason_required": True, "all_checklist_items_required": True, "automatic_approval_allowed": False, "live_trading_approval_allowed": False, "network_enabled": False}


def input_fixture(review, decision="APPROVE_PAPER"):
    return {"selected_decision": decision, "operator_name": "James Park", "operator_signature": "James Park / manually signed", "signed_at": "2026-07-30T20:30:00+00:00", "reason": "Reviewed all paper-only safety controls.", "checklist_confirmations": [{"review_index": x["review_index"], "review_item": x["review_item"], "operator_confirmed": True} for x in review["review_checklist"]]}


class TestV752E(unittest.TestCase):
    def build(self, decision="APPROVE_PAPER"):
        r = review_fixture(); return build_decision_record(r, input_fixture(r, decision), config_fixture(), "2026-07-30T20:31:00+00:00")
    def test_pass(self): self.assertEqual(self.build()["status"], "PASS")
    def test_version_schema(self):
        x=self.build(); self.assertEqual(x["version"], "75.2E"); self.assertEqual(x["schema_version"], "v75.2e.paper_operator_decision_record.1")
    def test_approve_state(self):
        x=self.build(); self.assertEqual(x["next_state"], "READY_FOR_PAPER_ACTIVATION_AUTHORIZATION"); self.assertTrue(x["activation_gate"]["paper_activation_preparation_allowed"])
    def test_reject_state(self):
        x=self.build("REJECT"); self.assertEqual(x["next_state"], "PAPER_DEPLOYMENT_REJECTED"); self.assertFalse(x["activation_gate"]["paper_activation_preparation_allowed"])
    def test_hold_state(self):
        x=self.build("HOLD"); self.assertEqual(x["next_state"], "PAPER_DEPLOYMENT_ON_HOLD")
    def test_activation_still_blocked(self): self.assertFalse(self.build()["activation_gate"]["activation_allowed"])
    def test_live_false(self): self.assertFalse(self.build()["approved_for_live"])
    def test_network_false(self): self.assertFalse(self.build()["network_used"])
    def test_checklist_confirmed(self): self.assertTrue(all(x["operator_confirmed"] for x in self.build()["confirmed_checklist"]))
    def test_signature_verified(self): self.assertTrue(self.build()["operator_record"]["signature_verified"])
    def test_hash(self):
        x=self.build(); h=x.pop("paper_operator_decision_record_sha256"); self.assertEqual(h, sha256_of(x))
    def test_deterministic_id(self):
        a=deterministic_decision_id("R","H","APPROVE_PAPER","T"); b=deterministic_decision_id("R","H","APPROVE_PAPER","T"); self.assertEqual(a,b)
    def test_bad_review_integrity(self):
        r=review_fixture(); r["review_id"]="BAD"; self.assertRaises(PaperOperatorDecisionError, build_decision_record, r, input_fixture(review_fixture()), config_fixture())
    def test_bad_review_state(self):
        r=review_fixture(); r.pop("paper_operator_review_package_sha256"); r["review_state"]="BAD"; r=with_hash(r,"paper_operator_review_package_sha256"); self.assertRaises(PaperOperatorDecisionError, build_decision_record, r, input_fixture(r), config_fixture())
    def test_invalid_decision(self):
        r=review_fixture(); d=input_fixture(r); d["selected_decision"]="LIVE"; self.assertRaises(PaperOperatorDecisionError, build_decision_record, r,d,config_fixture())
    def test_missing_name(self):
        r=review_fixture(); d=input_fixture(r); d["operator_name"]=""; self.assertRaises(PaperOperatorDecisionError, build_decision_record,r,d,config_fixture())
    def test_missing_signature(self):
        r=review_fixture(); d=input_fixture(r); d["operator_signature"]=""; self.assertRaises(PaperOperatorDecisionError, build_decision_record,r,d,config_fixture())
    def test_missing_reason(self):
        r=review_fixture(); d=input_fixture(r); d["reason"]="no"; self.assertRaises(PaperOperatorDecisionError, build_decision_record,r,d,config_fixture())
    def test_bad_signed_at(self):
        r=review_fixture(); d=input_fixture(r); d["signed_at"]="2026-07-30"; self.assertRaises(PaperOperatorDecisionError, build_decision_record,r,d,config_fixture())
    def test_unconfirmed_item(self):
        r=review_fixture(); d=input_fixture(r); d["checklist_confirmations"][0]["operator_confirmed"]=False; self.assertRaises(PaperOperatorDecisionError, build_decision_record,r,d,config_fixture())
    def test_mismatched_item(self):
        r=review_fixture(); d=input_fixture(r); d["checklist_confirmations"][0]["review_item"]="BAD"; self.assertRaises(PaperOperatorDecisionError, build_decision_record,r,d,config_fixture())
    def test_bad_config(self):
        r=review_fixture(); c=config_fixture(); c["automatic_approval_allowed"]=True; self.assertRaises(PaperOperatorDecisionError, build_decision_record,r,input_fixture(r),c)
    def test_main_success_failure(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); r=review_fixture(); d=input_fixture(r)
            (p/'r.json').write_text(json.dumps(r),encoding='utf-8'); (p/'d.json').write_text(json.dumps(d),encoding='utf-8'); (p/'c.json').write_text(json.dumps(config_fixture()),encoding='utf-8')
            self.assertEqual(main(['--input',str(p/'r.json'),'--decision-input',str(p/'d.json'),'--config',str(p/'c.json'),'--output-dir',str(p/'out')]),0)
            self.assertTrue((p/'out'/'paper_operator_decision_record_v75_2e.json').is_file())
            self.assertEqual(main(['--input',str(p/'missing.json'),'--decision-input',str(p/'d.json'),'--config',str(p/'c.json'),'--output-dir',str(p/'bad')]),1)

if __name__ == '__main__': unittest.main()
