import json,tempfile,unittest
from pathlib import Path
from tools.offline_paper_order_generation_authorization_v75_2t import *

TS="2026-07-30T21:50:00+00:00"; NONCE="0123456789abcdef0123456789abcdef"

def source_fixture():
    intents=[{"authorization_id":"OIA-A","broker_routed":False,"created_at":"2026-07-30T21:40:00+00:00",
              "fill_simulated":False,"intent_action":"BUY","intent_type":"MARKET_REFERENCE_ONLY",
              "network_used":False,"order_created":False,"order_intent_id":"INT-A","order_submitted":False,
              "quantity":1,"reference_price":633.5,"signal_action":"BUY","signal_id":"SIG-A","symbol":"SPY"}]
    checks=[{"check_index":1,"check":"A","state":"PASS"}]; ledger=[{"ledger_index":1,"event":"A","state":"PASS"}]
    s={"status":"PASS","validation_id":"OIV-A","validation_state":"READY_FOR_ORDER_GENERATION_AUTHORIZATION",
       "execution_id":"OIE-A","authorization_id":"OIA-A","session_id":"PAPER-A","cycle_id":"PCS-A",
       "cycle_sequence":1,"champion_candidate_id":"CAND-A",
       "validated_order_intent_summary":{"buy_intent_count":1,"no_action_intent_count":0,
         "order_intent_count":1,"sell_intent_count":0,"symbols":["SPY"],"total_intended_quantity":1},
       "validated_order_intents":intents,"validation_checks":checks,"validation_checks_sha256":sha256_of(checks),
       "validation_ledger":ledger,"validation_ledger_sha256":sha256_of(ledger),
       "source_order_intent_execution_sha256":"a"*64,"source_order_intent_package_sha256":"b"*64,
       "validation_gate":{"order_intent_validated":True,"order_generation_authorization_allowed":True,
         "order_generation_allowed":False,"fill_simulation_allowed":False,"paper_orders_allowed":False,
         "live_orders_allowed":False,"network_allowed":False,"next_version":"75.2T"},
       "order_generation_allowed":False,"fill_simulation_allowed":False,"paper_orders_allowed":False,
       "live_orders_allowed":False,"network_allowed":False,"broker_connection_allowed":False,
       "orders_created":0,"orders_submitted":0,"approved_for_live":False,"network_used":False,
       "safety_lock":{"broker_connected":False,"broker_credentials_required":False,
         "external_side_effects_allowed":False,"live_orders_enabled":False,
         "live_trading_approval_allowed":False,"lock_state":"ENFORCED","network_enabled":False},
       "schema_version":"v75.2s.offline_paper_order_intent_validation.1","version":"75.2S"}
    s["offline_paper_order_intent_validation_sha256"]=sha256_of(s)
    return s

def config_fixture():
    return {"authorization_ttl_seconds":900,
      "authorization_scope":"OFFLINE_PAPER_ORDER_OBJECT_CREATION_ONLY",
      "require_source_integrity":True,"require_validated_order_intents":True,
      "require_intent_identity_lock":True,"require_single_use_token":True,
      "require_zero_orders":True,"require_safety_lock":True,
      "order_object_creation_allowed":False,"order_submission_allowed":False,
      "fill_simulation_allowed":False,"paper_orders_allowed":False,
      "live_orders_allowed":False,"network_allowed":False,
      "broker_connection_allowed":False,"external_side_effects_allowed":False}

class TestV752T(unittest.TestCase):
    def build(self): return build_authorization(source_fixture(),config_fixture(),TS,NONCE)
    def rehash(self,s):
        s.pop("offline_paper_order_intent_validation_sha256",None)
        s["offline_paper_order_intent_validation_sha256"]=sha256_of(s)
    def test_pass(self): self.assertEqual(self.build()["status"],"PASS")
    def test_state(self): self.assertEqual(self.build()["authorization_state"],"AUTHORIZED_NOT_EXECUTED")
    def test_scope(self): self.assertEqual(self.build()["authorization_scope"],"OFFLINE_PAPER_ORDER_OBJECT_CREATION_ONLY")
    def test_authorized(self): self.assertTrue(self.build()["order_generation_authorized"])
    def test_not_executed(self): self.assertFalse(self.build()["order_generation_executed"])
    def test_manifest(self):
        x=self.build()["authorized_order_intent_manifest"][0]
        self.assertEqual(x["symbol"],"SPY"); self.assertEqual(x["side"],"BUY")
    def test_token(self):
        t=self.build()["authorization_token"]
        self.assertTrue(t["single_use"]); self.assertFalse(t["consumed"])
    def test_gate(self): self.assertTrue(self.build()["authorization_gate"]["order_object_creation_execution_allowed"])
    def test_creation_blocked(self): self.assertFalse(self.build()["authorization_gate"]["order_object_creation_allowed"])
    def test_orders_zero(self): self.assertEqual(self.build()["orders_created"],0)
    def test_hash(self):
        x=self.build(); h=x.pop("offline_paper_order_generation_authorization_sha256"); self.assertEqual(h,sha256_of(x))
    def test_checks(self): self.assertEqual(len(self.build()["authorization_checks"]),12)
    def test_ledger(self): self.assertEqual(len(self.build()["authorization_ledger"]),6)
    def test_bad_integrity(self):
        s=source_fixture(); s["cycle_id"]="BAD"
        self.assertRaises(OrderGenerationAuthorizationError,build_authorization,s,config_fixture(),TS,NONCE)
    def test_bad_state(self):
        s=source_fixture(); s["validation_state"]="BAD"; self.rehash(s)
        self.assertRaises(OrderGenerationAuthorizationError,build_authorization,s,config_fixture(),TS,NONCE)
    def test_duplicate_intent(self):
        s=source_fixture(); s["validated_order_intents"].append(dict(s["validated_order_intents"][0]))
        s["validated_order_intent_summary"]["order_intent_count"]=2; self.rehash(s)
        self.assertRaises(OrderGenerationAuthorizationError,build_authorization,s,config_fixture(),TS,NONCE)
    def test_no_action_only(self):
        s=source_fixture(); s["validated_order_intents"][0]["intent_action"]="NO_ACTION"; self.rehash(s)
        self.assertRaises(OrderGenerationAuthorizationError,build_authorization,s,config_fixture(),TS,NONCE)
    def test_side_effect(self):
        s=source_fixture(); s["validated_order_intents"][0]["order_created"]=True; self.rehash(s)
        self.assertRaises(OrderGenerationAuthorizationError,build_authorization,s,config_fixture(),TS,NONCE)
    def test_bad_ttl(self):
        c=config_fixture(); c["authorization_ttl_seconds"]=30
        self.assertRaises(OrderGenerationAuthorizationError,build_authorization,source_fixture(),c,TS,NONCE)
    def test_unsafe_config(self):
        c=config_fixture(); c["order_object_creation_allowed"]=True
        self.assertRaises(OrderGenerationAuthorizationError,build_authorization,source_fixture(),c,TS,NONCE)
    def test_main(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"s.json").write_text(json.dumps(source_fixture())); (p/"c.json").write_text(json.dumps(config_fixture()))
            self.assertEqual(main(["--input",str(p/"s.json"),"--config",str(p/"c.json"),"--output-dir",str(p/"out"),"--issued-at",TS,"--nonce",NONCE]),0)
            self.assertTrue((p/"out"/"offline_paper_order_generation_authorization_v75_2t.json").exists())
    def test_main_missing(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"c.json").write_text(json.dumps(config_fixture()))
            self.assertEqual(main(["--input",str(p/"missing"),"--config",str(p/"c.json"),"--output-dir",str(p/"out")]),1)

if __name__=="__main__": unittest.main()
