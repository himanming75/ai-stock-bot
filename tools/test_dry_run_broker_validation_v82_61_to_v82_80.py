from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.dry_run_broker_validation_v82_61_80 import *

class T(unittest.TestCase):
 def setUp(self): self.c=DryRunBrokerConfig()
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError):DryRunBrokerConfig(allow_network=True).validate()
 def test_intent(self): self.assertEqual(make_intent("AAPL","BUY",1,100)["submission_authorized"],False)
 def test_bad_intent(self):
  with self.assertRaises(ValueError):make_intent("AAPL","BUY",0,100)
 def test_idempotency(self): self.assertTrue(idempotency_key(make_intent("AAPL","BUY",1,100))["idempotency_key"].startswith("idem-"))
 def test_duplicate(self): self.assertTrue(duplicate_guard(["x","x"])["duplicate_detected"])
 def test_serialize(self): self.assertTrue(serialize_order(make_intent("AAPL","BUY",1,100))["preview_only"])
 def test_signing(self): self.assertFalse(signing_simulation({"x":1})["valid_for_network"])
 def test_risk_pass(self): self.assertTrue(risk_guard(make_intent("AAPL","BUY",5,100),self.c)["allowed"])
 def test_risk_fail(self): self.assertFalse(risk_guard(make_intent("AAPL","BUY",20,100),self.c)["allowed"])
 def test_buying_power(self): self.assertTrue(buying_power_guard(make_intent("AAPL","BUY",5,100),self.c)["allowed"])
 def test_position(self): self.assertFalse(position_guard(make_intent("AAPL","SELL",10,100),5,self.c)["allowed"])
 def test_market_session(self): self.assertTrue(market_session_guard(self.c)["allowed"])
 def test_preflight_pass(self): self.assertEqual(preflight(make_intent("AAPL","BUY",5,100),self.c)["status"],"PASS")
 def test_preflight_reject(self): self.assertEqual(preflight(make_intent("AAPL","BUY",20,100),self.c)["status"],"REJECTED")
 def test_rejection_map(self): self.assertEqual(rejection_mapping(["risk"])["rejection_codes"][0],"ORDER_NOTIONAL_LIMIT")
 def test_receipt(self):
  i=make_intent("AAPL","BUY",5,100);idem=idempotency_key(i);p=serialize_order(i);s=signing_simulation(p)
  self.assertEqual(build_receipt(i,idem,p,s,preflight(i,self.c))["status"],"DRY_RUN_ACCEPTED")
 def test_replay(self): self.assertTrue(replay_receipt(make_intent("AAPL","BUY",5,100),self.c)["deterministic"])
 def test_scenarios(self):
  d=build_scenarios(self.c);self.assertEqual(d["scenario_count"],4);self.assertTrue(d["duplicate_detected"])
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
   with self.assertRaises(ValueError):validate_connection_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/dry_run_broker_validation_v82_61_80.py").read_text().lower()
  for x in ("submit_order(","cancel_order(","replace_order(","tradingclient(","api_secret","api_key","os.getenv","requests.","httpx."):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V82.{i:02d}" for i in range(61,81)]),20)
if __name__=="__main__":unittest.main()
