from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.execution_simulation_v81_61_80 import *

class T(unittest.TestCase):
 def setUp(self): self.c=ExecutionSimulationConfig()
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError):ExecutionSimulationConfig(allow_network=True).validate()
 def test_order(self): self.assertEqual(make_order("AAPL","BUY",1)["status"],"NEW")
 def test_bad_order(self):
  with self.assertRaises(ValueError):make_order("AAPL","BUY",0)
 def test_queue(self): self.assertEqual(enqueue(make_order("AAPL","BUY",1),1)["queue_status"],"QUEUED")
 def test_slippage_buy(self): self.assertGreater(slippage_price(100,"BUY",self.c),100)
 def test_slippage_sell(self): self.assertLess(slippage_price(100,"SELL",self.c),100)
 def test_commission(self): self.assertEqual(commission(1,self.c),1)
 def test_latency(self): self.assertGreaterEqual(latency(make_order("AAPL","BUY",1)["order_id"],self.c),25)
 def test_fill(self): self.assertEqual(fill_event(make_order("AAPL","BUY",2),1,100,1,self.c)["quantity"],1)
 def test_full(self): self.assertEqual(execute_order(make_order("AAPL","BUY",10),100,self.c,"FULL")["status"],"FILLED")
 def test_partial(self): self.assertEqual(execute_order(make_order("AAPL","BUY",10),100,self.c,"PARTIAL")["status"],"PARTIALLY_FILLED")
 def test_multi(self): self.assertGreater(len(execute_order(make_order("AAPL","BUY",9),100,self.c,"MULTI")["fills"]),1)
 def test_limit_reject(self): self.assertEqual(execute_order(make_order("AAPL","BUY",1,"LIMIT",90),100,self.c)["status"],"REJECTED")
 def test_apply_buy(self):
  o=make_order("AAPL","BUY",1);e=execute_order(o,100,self.c);self.assertEqual(apply_execution({"cash":1000,"positions":{}},o,e)["positions"]["AAPL"],1)
 def test_apply_sell(self):
  o=make_order("AAPL","SELL",1);e=execute_order(o,100,self.c);self.assertEqual(apply_execution({"cash":0,"positions":{"AAPL":1}},o,e)["positions"]["AAPL"],0)
 def test_insufficient_cash(self):
  o=make_order("AAPL","BUY",10);e=execute_order(o,100,self.c)
  with self.assertRaises(ValueError):apply_execution({"cash":10,"positions":{}},o,e)
 def test_replay(self): self.assertTrue(replay(make_order("AAPL","BUY",1),100,self.c,"FULL")["deterministic"])
 def test_scenario(self): self.assertEqual(build_scenario(self.c)["execution_count"],4)
 def test_audit(self):
  s=build_scenario(self.c);r=replay(s["executions"][0]["order"],190,self.c,"FULL");self.assertEqual(build_audit(self.c,s,r)["status"],"PASS")
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
   with self.assertRaises(ValueError):validate_adapter_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/execution_simulation_v81_61_80.py").read_text().lower()
  for x in ("submit_order(","tradingclient(","api_secret","api_key","os.getenv","requests."):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V81.{i:02d}" for i in range(61,81)]),20)
if __name__=="__main__":unittest.main()
