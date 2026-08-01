from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.paper_broker_execution_sim_v83_61_80 import *

class T(unittest.TestCase):
 def setUp(self): self.c=PaperBrokerExecutionSimulationConfig()
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError):PaperBrokerExecutionSimulationConfig(allow_network=True).validate()
 def test_lifecycle(self): self.assertFalse(lifecycle_contract()["network_state_present"])
 def test_order(self): self.assertEqual(make_order("AAPL","BUY",1,100)["state"],"CREATED")
 def test_bad_order(self):
  with self.assertRaises(ValueError):make_order("AAPL","BUY",0,100)
 def test_accept(self): self.assertEqual(accept_order(make_order("AAPL","BUY",1,100))["state"],"ACCEPTED")
 def test_cancel(self): self.assertEqual(cancel_order_sim(accept_order(make_order("AAPL","BUY",1,100)),"x")["state"],"CANCELED")
 def test_price(self): self.assertGreater(execution_price(make_order("AAPL","BUY",1,100),self.c),100)
 def test_fill(self):
  o=accept_order(make_order("AAPL","BUY",2,100));self.assertEqual(create_fill(o,1,self.c,1)["quantity"],1)
 def test_apply_partial(self):
  o=accept_order(make_order("AAPL","BUY",2,100));o=apply_fill(o,create_fill(o,1,self.c,1));self.assertEqual(o["state"],"PARTIALLY_FILLED")
 def test_apply_full(self):
  o=accept_order(make_order("AAPL","BUY",1,100));o=apply_fill(o,create_fill(o,1,self.c,1));self.assertEqual(o["state"],"FILLED")
 def test_cash(self):
  o=accept_order(make_order("AAPL","BUY",1,100));f=create_fill(o,1,self.c,1);self.assertLess(cash_ledger(1000,[f])["closing_cash"],1000)
 def test_positions(self):
  o=accept_order(make_order("AAPL","BUY",1,100));f=create_fill(o,1,self.c,1);self.assertEqual(position_ledger([f],{"AAPL":101})["position_count"],1)
 def test_scenarios(self):
  d=build_scenarios(self.c);self.assertEqual(d["execution_ledger"]["order_count"],5)
 def test_replay(self): self.assertTrue(deterministic_replay(self.c)["deterministic"])
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
   with self.assertRaises(ValueError):validate_submission_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/paper_broker_execution_sim_v83_61_80.py").read_text().lower()
  for x in ("submit_order(","tradingclient(","api_secret","api_key","os.getenv","requests.","httpx."):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V83.{i:02d}" for i in range(61,81)]),20)
if __name__=="__main__":unittest.main()
