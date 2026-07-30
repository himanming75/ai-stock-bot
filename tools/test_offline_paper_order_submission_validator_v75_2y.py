import json,tempfile,unittest
from pathlib import Path
from tools.offline_paper_order_submission_validator_v75_2y import *

TS="2026-07-30T22:15:00+00:00"

def cfg():
    return {"validation_scope":"OFFLINE_PAPER_ORDER_SUBMISSION_VALIDATION_ONLY",
      "required_order_state":"SUBMITTED_OFFLINE_REFERENCE",
      "require_execution_integrity":True,"require_package_integrity":True,
      "require_consumed_token_integrity":True,"require_submission_id_recalculation":True,
      "require_zero_external_orders":True,"require_zero_broker_routes":True,
      "require_zero_fills":True,"require_safety_lock":True,
      "external_order_submission_allowed":False,"broker_routing_allowed":False,
      "fill_simulation_allowed":False,"paper_broker_allowed":False,
      "live_orders_allowed":False,"network_allowed":False,
      "broker_connection_allowed":False,"external_side_effects_allowed":False}

def src():
    submitted_at="2026-07-30T22:10:00+00:00"
    sid=expected_submission_id("OSE-A","PORD-AAAAAAAAAAAAAAAA",submitted_at)
    order={"authorization_id":"OSA-A","broker_routed":False,
      "external_side_effects":False,"external_submission":False,
      "fill_simulated":False,"filled":False,"network_used":False,
      "offline_submission_id":sid,"order_intent_id":"INT-A",
      "order_state":"SUBMITTED_OFFLINE_REFERENCE","order_type":"MARKET_REFERENCE_ONLY",
      "paper_order_id":"PORD-AAAAAAAAAAAAAAAA","previous_order_state":"CREATED_NOT_SUBMITTED",
      "quantity":1,"reference_price":633.5,"side":"BUY",
      "submitted_at":submitted_at,"submitted_offline":True,"symbol":"SPY","time_in_force":"DAY"}
    package={"authorization_id":"OSA-A","broker_routes_created":0,
      "champion_candidate_id":"CAND-A","cycle_id":"PCS-A","cycle_sequence":1,
      "executed_at":submitted_at,"execution_id":"OGE-A","external_orders_submitted":0,
      "fills_created":0,"immutable":True,"network_source":False,"offline_only":True,
      "session_id":"PAPER-A","submission_execution_id":"OSE-A",
      "submitted_order_count":1,"submitted_orders":[order],"validation_id":"OOV-A"}
    token={"authorization_id":"OSA-A","authorized_paper_order_ids":["PORD-AAAAAAAAAAAAAAAA"],
      "consumed":True,"consumed_at":submitted_at,"expires_at":"2026-07-30T22:20:00+00:00",
      "issued_at":"2026-07-30T22:05:00+00:00","nonce":"n",
      "scope":"OFFLINE_PAPER_ORDER_SUBMISSION_EXECUTION_ONLY","single_use":True,
      "token_sha256":"x","token_state":"CONSUMED","validation_id":"OOV-A"}
    checks=[{"check_index":1,"check":"A","state":"PASS"}]
    ledger=[{"ledger_index":1,"event":"A","state":"PASS"}]
    s={"status":"PASS","authorization_id":"OSA-A","authorization_source_id":"OGA-A",
      "authorization_state":"CONSUMED","broker_connection_allowed":False,
      "broker_routes_created":0,"broker_routing_allowed":False,
      "champion_candidate_id":"CAND-A","consumed_authorization_token":token,
      "consumed_authorization_token_sha256":sha256_of(token),
      "cycle_id":"PCS-A","cycle_sequence":1,"execution_checks":checks,
      "execution_checks_sha256":sha256_of(checks),"execution_gate":{
        "broker_routing_allowed":False,"external_order_submission_allowed":False,
        "fill_simulation_allowed":False,"live_orders_allowed":False,
        "network_allowed":False,"next_version":"75.2Y","offline_submission_recorded":True,
        "paper_broker_allowed":False,"submission_validation_allowed":True},
      "execution_id":"OGE-A","execution_ledger":ledger,
      "execution_ledger_sha256":sha256_of(ledger),
      "execution_state":"READY_FOR_SUBMISSION_VALIDATION",
      "external_order_submission_allowed":False,"external_orders_submitted":0,
      "fill_simulation_allowed":False,"fills_created":0,"live_orders_allowed":False,
      "network_allowed":False,"network_used":False,"offline_submission_package":package,
      "offline_submission_package_sha256":sha256_of(package),
      "offline_submissions_recorded":1,"order_submission_authorized":True,
      "order_submission_executed":True,"paper_broker_allowed":False,
      "safety_lock":{"broker_connected":False,"broker_credentials_required":False,
        "external_side_effects_allowed":False,"live_orders_enabled":False,
        "live_trading_approval_allowed":False,"lock_state":"ENFORCED","network_enabled":False},
      "schema_version":"v75.2x.offline_paper_order_submission_execution.1",
      "session_id":"PAPER-A","source_order_generation_execution_sha256":"a"*64,
      "source_order_object_validation_sha256":"b"*64,
      "source_order_submission_authorization_sha256":"c"*64,
      "submission_execution_id":"OSE-A","token_consumed":True,
      "validation_id":"OOV-A","version":"75.2X","approved_for_live":False}
    s["offline_paper_order_submission_execution_sha256"]=sha256_of(s)
    return s

class TestV752Y(unittest.TestCase):
    def build(self): return build_validation(src(),cfg(),TS)
    def rehash(self,s):
        s.pop("offline_paper_order_submission_execution_sha256",None)
        s["offline_paper_order_submission_execution_sha256"]=sha256_of(s)
    def rehash_package(self,s):
        s["offline_submission_package_sha256"]=sha256_of(s["offline_submission_package"]); self.rehash(s)
    def test_pass(self): self.assertEqual(self.build()["status"],"PASS")
    def test_state(self): self.assertEqual(self.build()["validation_state"],"READY_FOR_FILL_SIMULATION_AUTHORIZATION")
    def test_count(self): self.assertEqual(self.build()["validated_submission_count"],1)
    def test_gate(self): self.assertTrue(self.build()["validation_gate"]["fill_simulation_authorization_allowed"])
    def test_submission(self):
        o=self.build()["validated_submissions"][0]
        self.assertEqual(o["order_state"],"SUBMITTED_OFFLINE_REFERENCE")
        self.assertEqual(o["validation_state"],"PASS")
    def test_hash(self):
        x=self.build(); h=x.pop("offline_paper_order_submission_validation_sha256")
        self.assertEqual(h,sha256_of(x))
    def test_validated_hash(self):
        x=self.build(); self.assertEqual(x["validated_submissions_sha256"],sha256_of(x["validated_submissions"]))
    def test_checks(self): self.assertEqual(len(self.build()["validation_checks"]),12)
    def test_ledger(self): self.assertEqual(len(self.build()["validation_ledger"]),6)
    def test_bad_integrity(self):
        s=src(); s["cycle_id"]="BAD"
        self.assertRaises(OrderSubmissionValidationError,build_validation,s,cfg(),TS)
    def test_bad_submission_id(self):
        s=src(); s["offline_submission_package"]["submitted_orders"][0]["offline_submission_id"]="OSUB-"+"0"*16
        self.rehash_package(s)
        self.assertRaises(OrderSubmissionValidationError,build_validation,s,cfg(),TS)
    def test_duplicate(self):
        s=src(); o=dict(s["offline_submission_package"]["submitted_orders"][0])
        s["offline_submission_package"]["submitted_orders"].append(o)
        s["offline_submission_package"]["submitted_order_count"]=2
        s["offline_submissions_recorded"]=2
        s["consumed_authorization_token"]["authorized_paper_order_ids"]*=2
        s["consumed_authorization_token_sha256"]=sha256_of(s["consumed_authorization_token"])
        self.rehash_package(s)
        self.assertRaises(OrderSubmissionValidationError,build_validation,s,cfg(),TS)
    def test_bad_state(self):
        s=src(); s["offline_submission_package"]["submitted_orders"][0]["order_state"]="CREATED_NOT_SUBMITTED"
        self.rehash_package(s)
        self.assertRaises(OrderSubmissionValidationError,build_validation,s,cfg(),TS)
    def test_external_submission(self):
        s=src(); s["offline_submission_package"]["submitted_orders"][0]["external_submission"]=True
        self.rehash_package(s)
        self.assertRaises(OrderSubmissionValidationError,build_validation,s,cfg(),TS)
    def test_broker_route(self):
        s=src(); s["offline_submission_package"]["submitted_orders"][0]["broker_routed"]=True
        self.rehash_package(s)
        self.assertRaises(OrderSubmissionValidationError,build_validation,s,cfg(),TS)
    def test_token_window(self):
        s=src(); s["consumed_authorization_token"]["consumed_at"]="2026-07-30T22:21:00+00:00"
        s["consumed_authorization_token_sha256"]=sha256_of(s["consumed_authorization_token"]); self.rehash(s)
        self.assertRaises(OrderSubmissionValidationError,build_validation,s,cfg(),TS)
    def test_unsafe_config(self):
        c=cfg(); c["network_allowed"]=True
        self.assertRaises(OrderSubmissionValidationError,build_validation,src(),c,TS)
    def test_main(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"s.json").write_text(json.dumps(src())); (p/"c.json").write_text(json.dumps(cfg()))
            self.assertEqual(main(["--input",str(p/"s.json"),"--config",str(p/"c.json"),"--output-dir",str(p/"out"),"--validated-at",TS]),0)
    def test_main_missing(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"c.json").write_text(json.dumps(cfg()))
            self.assertEqual(main(["--input",str(p/"missing"),"--config",str(p/"c.json"),"--output-dir",str(p/"out")]),1)

if __name__=="__main__": unittest.main()
