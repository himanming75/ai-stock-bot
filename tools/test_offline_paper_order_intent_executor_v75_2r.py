import json,tempfile,unittest
from pathlib import Path
from tools.offline_paper_order_intent_executor_v75_2r import *

TS="2026-07-30T21:40:00+00:00"

def source_fixture():
    manifest=[{"action":"BUY","as_of":"2026-07-30T15:30:00+00:00","latest_price":633.5,
               "order_created":False,"order_intent_creation_authorized":True,"order_submitted":False,
               "signal_id":"SIG-A","symbol":"SPY"}]
    token_material={"authorization_id":"OIA-A","validation_id":"SOV-A","issued_at":"2026-07-30T21:35:00+00:00",
                    "expires_at":"2026-07-30T21:50:00+00:00","nonce":"n",
                    "scope":"OFFLINE_PAPER_ORDER_INTENT_CREATION_ONLY","authorized_signal_ids":["SIG-A"]}
    token={**token_material,"token_sha256":sha256_of(token_material),"single_use":True,"consumed":False,
           "consumed_at":None,"token_state":"ISSUED_NOT_CONSUMED"}
    checks=[{"check_index":1,"check":"A","state":"PASS"}]; ledger=[{"ledger_index":1,"event":"A","state":"PASS"}]
    s={"status":"PASS","authorization_id":"OIA-A","authorization_scope":"OFFLINE_PAPER_ORDER_INTENT_CREATION_ONLY",
       "authorization_state":"AUTHORIZED_NOT_EXECUTED","order_intent_authorized":True,"order_intent_created":False,
       "token_consumed":False,"authorization_token":token,"authorization_token_sha256":sha256_of(token),
       "authorized_signal_manifest":manifest,"authorized_signal_manifest_sha256":sha256_of(manifest),
       "authorization_checks":checks,"authorization_checks_sha256":sha256_of(checks),
       "authorization_ledger":ledger,"authorization_ledger_sha256":sha256_of(ledger),
       "validation_id":"SOV-A","signal_execution_id":"SGE-A","session_id":"PAPER-A","cycle_id":"PCS-A",
       "cycle_sequence":1,"champion_candidate_id":"CAND-A",
       "authorization_gate":{"order_intent_authorized":True,"order_intent_creation_execution_allowed":True,
                             "order_intent_creation_allowed":False,"order_generation_allowed":False,
                             "fill_simulation_allowed":False,"paper_orders_allowed":False,
                             "live_orders_allowed":False,"network_allowed":False,"next_version":"75.2R"},
       "order_intents_created":0,"order_generation_allowed":False,"fill_simulation_allowed":False,
       "paper_orders_allowed":False,"live_orders_allowed":False,"network_allowed":False,
       "broker_connection_allowed":False,"orders_created":0,"orders_submitted":0,
       "approved_for_live":False,"network_used":False,
       "safety_lock":{"broker_connected":False,"broker_credentials_required":False,
                      "external_side_effects_allowed":False,"live_orders_enabled":False,
                      "live_trading_approval_allowed":False,"lock_state":"ENFORCED","network_enabled":False},
       "schema_version":"v75.2q.offline_paper_order_intent_authorization.1","version":"75.2Q"}
    s["offline_paper_order_intent_authorization_sha256"]=sha256_of(s)
    return s

def config_fixture():
    return {"execution_scope":"OFFLINE_PAPER_ORDER_INTENT_CREATION_ONLY","default_quantity":1,
            "intent_type":"MARKET_REFERENCE_ONLY","require_authorization_integrity":True,
            "require_single_use_token":True,"require_token_unconsumed":True,"require_token_unexpired":True,
            "require_signal_manifest_integrity":True,"prevent_output_overwrite":True,
            "order_generation_allowed":False,"fill_simulation_allowed":False,"paper_orders_allowed":False,
            "live_orders_allowed":False,"network_allowed":False,"broker_connection_allowed":False,
            "external_side_effects_allowed":False}

class TestV752R(unittest.TestCase):
    def build(self): return build_execution(source_fixture(),config_fixture(),TS)
    def rehash(self,s):
        s.pop("offline_paper_order_intent_authorization_sha256",None)
        s["offline_paper_order_intent_authorization_sha256"]=sha256_of(s)
    def test_pass(self): self.assertEqual(self.build()["status"],"PASS")
    def test_state(self): self.assertEqual(self.build()["execution_state"],"READY_FOR_ORDER_INTENT_VALIDATION")
    def test_intent(self):
        x=self.build()["order_intent_package"]["order_intents"][0]
        self.assertEqual(x["intent_action"],"BUY"); self.assertEqual(x["quantity"],1)
    def test_token_consumed(self): self.assertTrue(self.build()["token_consumed"])
    def test_no_orders(self):
        x=self.build(); self.assertEqual(x["orders_created"],0); self.assertFalse(x["order_generation_allowed"])
    def test_gate(self): self.assertTrue(self.build()["execution_gate"]["order_intent_validation_allowed"])
    def test_hash(self):
        x=self.build(); h=x.pop("offline_paper_order_intent_execution_sha256"); self.assertEqual(h,sha256_of(x))
    def test_package_hash(self):
        x=self.build(); self.assertEqual(x["order_intent_package_sha256"],sha256_of(x["order_intent_package"]))
    def test_checks(self): self.assertEqual(len(self.build()["execution_checks"]),12)
    def test_ledger(self): self.assertEqual(len(self.build()["execution_ledger"]),6)
    def test_expired(self): self.assertRaises(OrderIntentExecutionError,build_execution,source_fixture(),config_fixture(),"2026-07-30T21:51:00+00:00")
    def test_before_issued(self): self.assertRaises(OrderIntentExecutionError,build_execution,source_fixture(),config_fixture(),"2026-07-30T21:34:00+00:00")
    def test_consumed(self):
        s=source_fixture(); s["authorization_token"]["consumed"]=True; s["authorization_token"]["token_state"]="CONSUMED"
        s["authorization_token_sha256"]=sha256_of(s["authorization_token"]); self.rehash(s)
        self.assertRaises(OrderIntentExecutionError,build_execution,s,config_fixture(),TS)
    def test_bad_integrity(self):
        s=source_fixture(); s["cycle_id"]="BAD"
        self.assertRaises(OrderIntentExecutionError,build_execution,s,config_fixture(),TS)
    def test_signal_lock(self):
        s=source_fixture(); s["authorization_token"]["authorized_signal_ids"]=["BAD"]
        mat={k:s["authorization_token"].get(k) for k in ("authorization_id","validation_id","issued_at","expires_at","nonce","scope","authorized_signal_ids")}
        s["authorization_token"]["token_sha256"]=sha256_of(mat); s["authorization_token_sha256"]=sha256_of(s["authorization_token"]); self.rehash(s)
        self.assertRaises(OrderIntentExecutionError,build_execution,s,config_fixture(),TS)
    def test_unsafe_config(self):
        c=config_fixture(); c["order_generation_allowed"]=True
        self.assertRaises(OrderIntentExecutionError,build_execution,source_fixture(),c,TS)
    def test_main(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"s.json").write_text(json.dumps(source_fixture())); (p/"c.json").write_text(json.dumps(config_fixture()))
            args=["--authorization",str(p/"s.json"),"--config",str(p/"c.json"),"--output-dir",str(p/"out"),"--executed-at",TS]
            self.assertEqual(main(args),0); self.assertEqual(main(args),1)
    def test_main_missing(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/"c.json").write_text(json.dumps(config_fixture()))
            self.assertEqual(main(["--authorization",str(p/"missing"),"--config",str(p/"c.json"),"--output-dir",str(p/"out")]),1)

if __name__=="__main__": unittest.main()
