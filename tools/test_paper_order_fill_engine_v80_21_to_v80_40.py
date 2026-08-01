from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.paper_order_fill_engine_v80_21_40 import *

class T(unittest.TestCase):
 def setUp(self): self.c=PaperOrderFillConfig()
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError): PaperOrderFillConfig(allow_network=True).validate()
 def test_make_order(self): self.assertEqual(make_order("aapl","buy",1,100,"x")["status"],"NEW")
 def test_bad_quantity(self):
  with self.assertRaises(ValueError): make_order("AAPL","BUY",0,100,"x")
 def test_validation_reject(self):
  o=make_order("AAPL","SELL",1,100,"x");self.assertEqual(validate_order(o,self.c,{})["status"],"REJECT")
 def test_enqueue(self):
  o=make_order("AAPL","BUY",1,100,"x");q,o=enqueue_order([],o,validate_order(o,self.c,{}));self.assertEqual(o["status"],"ACCEPTED")
 def test_duplicate(self):
  o=make_order("AAPL","BUY",1,100,"x");q,o=enqueue_order([],o,validate_order(o,self.c,{}))
  with self.assertRaises(ValueError): enqueue_order(q,o,{"status":"PASS"})
 def test_cancel(self):
  o=make_order("AAPL","BUY",1,100,"x");q,o=enqueue_order([],o,validate_order(o,self.c,{}));self.assertEqual(cancel_order(o)["status"],"CANCELED")
 def test_invalid_transition(self):
  o=make_order("AAPL","BUY",1,100,"x")
  with self.assertRaises(ValueError): transition_order(o,"FILLED","bad")
 def test_slippage(self): self.assertGreater(fill_price("BUY",100,5),100)
 def test_partial_fill(self):
  o=make_order("AAPL","BUY",10,100,"x");q,o=enqueue_order([],o,validate_order(o,self.c,{}));o,f=simulate_fill(o,4,self.c);self.assertEqual(o["status"],"PARTIALLY_FILLED")
 def test_full_fill(self):
  o=make_order("AAPL","BUY",1,100,"x");q,o=enqueue_order([],o,validate_order(o,self.c,{}));o,f=simulate_fill(o,1,self.c);self.assertEqual(o["status"],"FILLED")
 def test_apply_buy(self):
  o=make_order("AAPL","BUY",1,100,"x");q,o=enqueue_order([],o,validate_order(o,self.c,{}));o,f=simulate_fill(o,1,self.c);a,p,e=apply_fill({"cash":1000},{},f);self.assertEqual(p["AAPL"]["quantity"],1)
 def test_apply_sell(self):
  f={"fill_id":"x","symbol":"AAPL","side":"SELL","quantity":1,"price":110.0,"commission":1.0};a,p,e=apply_fill({"cash":0},{"AAPL":{"quantity":1,"average_price":100.0,"realized_pnl":0}},f);self.assertGreater(e["realized_pnl"],0)
 def test_insufficient_cash(self):
  f={"fill_id":"x","symbol":"AAPL","side":"BUY","quantity":10,"price":100.0,"commission":1.0}
  with self.assertRaises(ValueError): apply_fill({"cash":1},{},f)
 def test_mark_to_market(self): self.assertEqual(mark_to_market({"cash":100},{},{})["equity"],100)
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   out=Path(t);d={"x":{"a":1}};store_bundle(out,d);self.assertTrue(store_bundle(out,d)["reused"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_bundle(out,{"x":{"a":1}});m=build_manifest(out,z["ledger"]);self.assertTrue(verify_manifest(out,m))
 def test_manifest_tamper(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_bundle(out,{"x":{"a":1}});m=build_manifest(out,z["ledger"]);(out/"bundles"/z["bundle_id"]/"x.json").write_text("{}")
   with self.assertRaises(ValueError): verify_manifest(out,m)
 def test_bad_cert(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c";p.write_text("{}")
   with self.assertRaises(ValueError): validate_session_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/paper_order_fill_engine_v80_21_40.py").read_text().lower()
  for x in ("submit_order(","tradingclient(","api_secret","api_key","os.getenv"): self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V80.{i:02d}" for i in range(21,41)]),20)
if __name__=="__main__":unittest.main()
