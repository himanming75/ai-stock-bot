import json,tempfile,unittest
from pathlib import Path
from tools.offline_paper_order_submission_executor_v75_2x import *

TS="2026-07-30T22:10:00+00:00"

def cfg():
    return {"execution_scope":"OFFLINE_PAPER_ORDER_SUBMISSION_STATE_TRANSITION_ONLY",
      "submitted_order_state":"SUBMITTED_OFFLINE_REFERENCE",
      "require_authorization_integrity":True,"require_manifest_integrity":True,
      "require_single_use_token":True,"require_token_unconsumed":True,
      "require_token_unexpired":True,"prevent_output_overwrite":True,
      "broker_routing_allowed":False,"fill_simulation_allowed":False,
      "paper_broker_allowed":False,"live_orders_allowed":False,
      "network_allowed":False,"broker_connection_allowed":False,
      "external_side_effects_allowed":False}

def src():
    manifest=[{"broker_routed":False,"filled":False,"order_intent_id":"INT-A",
      "order_state":"CREATED_NOT_SUBMITTED","order_type":"MARKET_REFERENCE_ONLY",
      "paper_order_id":"PORD-AAAAAAAAAAAAAAAA","quantity":1,"reference_price":633.5,
      "side":"BUY","submission_execution_authorized":True,"submitted":False,
      "symbol":"SPY","time_in_force":"DAY"}]
    mat={"authorization_id":"OSA-A","validation_id":"OOV-A",
      "issued_at":"2026-07-30T22:05:00+00:00","expires_at":"2026-07-30T22:20:00+00:00",
      "nonce":"n","scope":"OFFLINE_PAPER_ORDER_SUBMISSION_EXECUTION_ONLY",
      "authorized_paper_order_ids":["PORD-AAAAAAAAAAAAAAAA"]}
    token={**mat,"token_sha256":sha256_of(mat),"single_use":True,
      "consumed":False,"consumed_at":None,"token_state":"ISSUED_NOT_CONSUMED"}
    checks=[{"check_index":1,"check":"A","state":"PASS"}]
    ledger=[{"ledger_index":1,"event":"A","state":"PASS"}]
    s={"status":"PASS","authorization_id":"OSA-A",
      "authorization_scope":"OFFLINE_PAPER_ORDER_SUBMISSION_EXECUTION_ONLY",
      "authorization_state":"AUTHORIZED_NOT_EXECUTED",
      "authorization_source_id":"OGA-A","order_submission_authorized":True,
      "order_submission_executed":False,"submission_execution_allowed":True,
      "order_submission_allowed":False,"token_consumed":False,
      "authorization_token":token,"authorization_token_sha256":sha256_of(token),
      "authorized_order_count":1,"authorized_order_manifest":manifest,
      "authorized_order_manifest_sha256":sha256_of(manifest),
      "authorization_checks":checks,"authorization_checks_sha256":sha256_of(checks),
      "authorization_ledger":ledger,"authorization_ledger_sha256":sha256_of(ledger),
      "authorization_gate":{"order_submission_authorized":True,
        "submission_execution_allowed":True,"order_submission_allowed":False,
        "broker_routing_allowed":False,"fill_simulation_allowed":False,
        "paper_broker_allowed":False,"live_orders_allowed":False,
        "network_allowed":False,"next_version":"75.2X"},
      "source_order_object_validation_sha256":"a"*64,
      "source_order_generation_execution_sha256":"b"*64,
      "validation_id":"OOV-A","execution_id":"OGE-A","session_id":"PAPER-A",
      "cycle_id":"PCS-A","cycle_sequence":1,"champion_candidate_id":"CAND-A",
      "broker_routing_allowed":False,"fill_simulation_allowed":False,
      "paper_broker_allowed":False,"live_orders_allowed":False,
      "network_allowed":False,"broker_connection_allowed":False,
      "orders_submitted":0,"fills_created":0,"approved_for_live":False,
      "network_used":False,"safety_lock":{"broker_connected":False,
      "broker_credentials_required":False,"external_side_effects_allowed":False,
      "live_orders_enabled":False,"live_trading_approval_allowed":False,
      "lock_state":"ENFORCED","network_enabled":False},
      "schema_version":"v75.2w.offline_paper_order_submission_authorization.1",
      "version":"75.2W"}
    s["offline_paper_order_submission_authorization_sha256"]=sha256_of(s)
    return s

class TestV752X(unittest.TestCase):
    def build(self): return build_execution(src(),cfg(),TS)
    def rehash(self,s):
        s.pop("offline_paper_order_submission_authorization_sha256",None)
        s["offline_paper_order_submission_authorization_sha256"]=sha256_of(s)
    def test_pass(self): self.assertEqual(self.build()["status"],"PASS")
    def test_state(self): self.assertEqual(self.build()["execution_state"],"READY_FOR_SUBMISSION_VALIDATION")
    def test_token(self): self.assertTrue(self.build()["token_consumed"])
    def test_count(self): self.assertEqual(self.build()["offline_submissions_recorded"],1)
    def test_order_state(self):
        o=self.build()["offline_submission_package"]["submitted_orders"][0]
        self.assertEqual(o["order_state"],"SUBMITTED_OFFLINE_REFERENCE")
        self.assertTrue(o["submitted_offline"]); self.assertFalse(o["external_submission"])
    def test_no_external(self): self.assertEqual(self.build()["external_orders_submitted"],0)
    def test_no_route(self): self.assertEqual(self.build()["broker_routes_created"],0)
    def test_no_fill(self): self.assertEqual(self.build()["fills_created"],0)
    def test_gate(self): self.assertTrue(self.build()["execution_gate"]["submission_validation_allowed"])
    def test_hash(self):
        x=self.build(); h=x.pop("offline_paper_order_submission_execution_sha256")
        self.assertEqual(h,sha256_of(x))
    def test_package_hash(self):
        x=self.build(); self.assertEqual(x["offline_submission_package_sha256"],sha256_of(x["offline_submission_package"]))
    def test_checks(self): self.assertEqual(len(self.build()["execution_checks"]),12)
    def test_ledger(self): self.assertEqual(len(self.build()["execution_ledger"]),6)
    def test_expired(self):
        self.assertRaises(OrderSubmissionExecutionError,build_execution,src(),cfg(),"2026-07-30T22:21:00+00:00")
    def test_before_issue(self):
        self.assertRaises(OrderSubmissionExecutionError,build_execution,src(),cfg(),"2026-07-30T22:04:00+00:00")
    def test_consumed(self):
        s=src(); s["authorization_token"]["consumed"]=True
        s["authorization_token"]["token_state"]="CONSUMED"
        s["authorization_token_sha256"]=sha256_of(s["authorization_token"]); self.rehash(s)
        self.assertRaises(OrderSubmissionExecutionError,build_execution,s,cfg(),TS)
    def test_bad_integrity(self):
        s=src(); s["cycle_id"]="BAD"
        self.assertRaises(OrderSubmissionExecutionError,build_execution,s,cfg(),TS)
    def test_unsafe_manifest(self):
        s=src(); s["authorized_order_manifest"][0]["broker_routed"]=True
        s["authorized_order_manifest_sha256"]=sha256_of(s["authorized_order_manifest"]); self.rehash(s)
        self.assertRaises(OrderSubmissionExecutionError,build_execution,s,cfg(),TS)
    def test_unsafe_config(self):
        c=cfg(); c["network_allowed"]=True
        self.assertRaises(OrderSubmissionExecutionError,build_execution,src(),c,TS)
    def test_main(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"s.json").write_text(json.dumps(src())); (p/"c.json").write_text(json.dumps(cfg()))
            args=["--authorization",str(p/"s.json"),"--config",str(p/"c.json"),
              "--output-dir",str(p/"out"),"--executed-at",TS]
            self.assertEqual(main(args),0); self.assertEqual(main(args),1)
    def test_main_missing(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"c.json").write_text(json.dumps(cfg()))
            self.assertEqual(main(["--authorization",str(p/"missing"),"--config",str(p/"c.json"),"--output-dir",str(p/"out")]),1)

if __name__=="__main__": unittest.main()
