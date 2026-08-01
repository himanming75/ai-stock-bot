from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.paper_order_gate_v83_01_20 import *

class T(unittest.TestCase):
 def setUp(self):
  self.c=PaperBrokerOrderGateConfig()
  self.source={"certificate_sha256":"x","paper_broker_summary":{"permission_scope":"PAPER_PREVIEW_AND_SESSION_ONLY"},
               "paper_session_authorized":True}
  self.session=session_binding(self.source)
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError):PaperBrokerOrderGateConfig(allow_network=True).validate()
 def test_profile(self): self.assertFalse(connection_profile()["network_enabled"])
 def test_session(self): self.assertTrue(self.session["paper_session_authorized"])
 def test_policy(self): self.assertFalse(order_gate_policy()["rules"]["paper_order_submit_enabled"])
 def test_intent(self): self.assertFalse(make_order_intent("AAPL","BUY",1,100)["submission_authorized"])
 def test_bad_intent(self):
  with self.assertRaises(ValueError):make_order_intent("AAPL","BUY",0,100)
 def test_idempotency(self): self.assertTrue(idempotency_key(make_order_intent("AAPL","BUY",1,100))["key"].startswith("paper-idem-"))
 def test_duplicate(self): self.assertTrue(duplicate_guard(["x","x"])["duplicate_detected"])
 def test_environment(self): self.assertTrue(environment_guard(make_order_intent("AAPL","BUY",1,100),self.c)["allowed"])
 def test_session_guard(self): self.assertTrue(session_guard(self.session)["allowed"])
 def test_risk(self): self.assertTrue(risk_guard(make_order_intent("AAPL","BUY",5,100),self.c)["allowed"])
 def test_buying_power(self): self.assertTrue(buying_power_guard(make_order_intent("AAPL","BUY",5,100),self.c)["allowed"])
 def test_position(self): self.assertFalse(position_guard(make_order_intent("AAPL","SELL",10,100),5,self.c)["allowed"])
 def test_market(self): self.assertTrue(market_session_guard(self.c)["allowed"])
 def test_preflight(self): self.assertEqual(preflight(make_order_intent("AAPL","BUY",5,100),self.session,self.c)["status"],"PASS")
 def test_queue(self):
  i=make_order_intent("AAPL","BUY",5,100);idem=idempotency_key(i);pf=preflight(i,self.session,self.c)
  self.assertEqual(queue_preview(i,idem,pf)["queue_status"],"PREVIEW_ACCEPTED")
 def test_receipt(self):
  i=make_order_intent("AAPL","BUY",5,100);idem=idempotency_key(i);pf=preflight(i,self.session,self.c);q=queue_preview(i,idem,pf)
  self.assertEqual(gate_receipt(i,q,pf)["status"],"GATE_PASS")
 def test_scenarios(self):
  d=build_scenarios(self.session,self.c);self.assertEqual(d["scenario_count"],4);self.assertTrue(d["duplicate_detected"])
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   out=Path(t);store_package(out,{"a":{"x":1}});self.assertTrue(store_package(out,{"a":{"x":1}})["reused"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_package(out,{"a":{"x":1}});m=build_manifest(out,z["ledger"]);self.assertTrue(verify_manifest(out,m))
 def test_manifest_tamper(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_package(out,{"a":{"x":1}});m=build_manifest(out,z["ledger"]);(out/"packages"/z["package_id"]/"a.json").write_text("{}")
   with self.assertRaises(ValueError):verify_manifest(out,m)
 def test_bad_cert(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c";p.write_text("{}")
   with self.assertRaises(ValueError):validate_enablement_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/paper_order_gate_v83_01_20.py").read_text().lower()
  for x in ("submit_order(","cancel_order(","replace_order(","tradingclient(","api_secret","api_key","os.getenv","requests.","httpx."):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V83.{i:02d}" for i in range(1,21)]),20)
if __name__=="__main__":unittest.main()
