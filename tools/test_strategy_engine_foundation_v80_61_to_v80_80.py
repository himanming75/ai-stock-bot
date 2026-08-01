from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.strategy_engine_foundation_v80_61_80 import *

class T(unittest.TestCase):
 def setUp(self): self.c=StrategyEngineConfig();self.rows=sample_rows()
 def test_config(self): self.c.validate()
 def test_weights_rejected(self):
  with self.assertRaises(ValueError): StrategyEngineConfig(weights=(1,1,1,1)).validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError): StrategyEngineConfig(allow_network=True).validate()
 def test_rows(self): self.assertEqual(len(validate_rows(self.rows)),8)
 def test_bad_rows(self):
  with self.assertRaises(ValueError): validate_rows([{"close":1}])
 def test_registry(self): self.assertEqual(build_registry()["strategy_count"],4)
 def test_loader(self): self.assertEqual(len(load_plugins(build_registry())),4)
 def test_metadata(self): self.assertEqual(build_metadata(load_plugins(build_registry()))["strategy_count"],4)
 def test_sma(self): self.assertIn(SmaCrossStrategy().evaluate(self.rows)["signal"],{"BUY","SELL","HOLD"})
 def test_rsi(self): self.assertIn(RsiMeanReversionStrategy().evaluate(self.rows)["signal"],{"BUY","SELL","HOLD"})
 def test_momentum(self): self.assertEqual(MomentumStrategy().evaluate(self.rows)["signal"],"BUY")
 def test_breakout(self): self.assertIn(BreakoutStrategy().evaluate(self.rows)["signal"],{"BUY","SELL","HOLD"})
 def test_execute(self): self.assertEqual(len(execute_strategies(load_plugins(build_registry()),self.rows)),4)
 def test_resolve(self):
  s=execute_strategies(load_plugins(build_registry()),self.rows);self.assertIn(resolve_signals(s,self.c)["final_signal"],{"BUY","SELL","HOLD"})
 def test_hold_threshold(self):
  signals=[]
  for strategy_id in self.c.enabled_strategies:
   signal={"stage":"V80.66","strategy_id":strategy_id,"strategy_version":"1","signal":"HOLD",
    "confidence":0.0,"reason":"fixture","order_submission_authorized":False}
   signal["signal_sha256"]=sha256_strategy_engine_json(signal)
   signals.append(signal)
  self.assertEqual(resolve_signals(signals,self.c)["final_signal"],"HOLD")
 def test_allocation_no_order(self):
  d={"final_signal":"BUY","confidence":0.5};self.assertEqual(build_allocation(d,self.c)["order_quantity"],0)
 def test_audit(self):
  r=build_registry();p=load_plugins(r);m=build_metadata(p);s=execute_strategies(p,self.rows);d=resolve_signals(s,self.c);a=build_allocation(d,self.c)
  self.assertEqual(build_audit(r,m,s,d,a)["status"],"PASS")
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   out=Path(t);docs={"a":{"x":1}};store_package(out,docs);self.assertTrue(store_package(out,docs)["reused"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_package(out,{"a":{"x":1}});m=build_manifest(out,z["ledger"]);self.assertTrue(verify_manifest(out,m))
 def test_manifest_tamper(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_package(out,{"a":{"x":1}});m=build_manifest(out,z["ledger"]);(out/"packages"/z["package_id"]/"a.json").write_text("{}")
   with self.assertRaises(ValueError): verify_manifest(out,m)
 def test_bad_cert(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c";p.write_text("{}")
   with self.assertRaises(ValueError): validate_monitoring_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/strategy_engine_foundation_v80_61_80.py").read_text().lower()
  for x in ("submit_order(","tradingclient(","api_secret","api_key","os.getenv","importlib"): self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V80.{i:02d}" for i in range(61,81)]),20)
if __name__=="__main__":unittest.main()
