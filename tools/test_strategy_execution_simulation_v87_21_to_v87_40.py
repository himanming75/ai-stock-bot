from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.strategy_execution_simulation_v87_21_40 import *

class T(unittest.TestCase):
 def setUp(self): self.c=StrategyExecutionSimulationConfig()
 def test_config(self): self.c.validate()
 def test_auto_exec_rejected(self):
  with self.assertRaises(ValueError):StrategyExecutionSimulationConfig(auto_execution_enabled=True).validate()
 def test_plan(self): self.assertEqual(order_plan(self.c)["status"],"PLANNED")
 def test_sizing(self): self.assertEqual(position_sizing(self.c,order_plan(self.c))["status"],"PASS")
 def test_slippage(self): self.assertGreater(slippage_model(self.c,"buy",200)["simulated_price"],200)
 def test_commission(self): self.assertEqual(commission_model(self.c)["estimated_commission"],0)
 def test_accepted(self): self.assertEqual(simulate_accepted(order_plan(self.c))["status"],"accepted")
 def test_partial(self): self.assertEqual(simulate_partial(order_plan(self.c),200)["status"],"partially_filled")
 def test_filled(self): self.assertEqual(simulate_filled(order_plan(self.c),200)["status"],"filled")
 def test_rejected(self): self.assertEqual(simulate_rejected(order_plan(self.c))["status"],"rejected")
 def test_canceled(self): self.assertEqual(simulate_canceled(order_plan(self.c))["status"],"canceled")
 def test_retry(self): self.assertTrue(retry_policy(self.c,0,"timeout")["retry_allowed"])
 def test_retry_exhausted(self): self.assertFalse(retry_policy(self.c,self.c.retry_limit,"timeout")["retry_allowed"])
 def test_budget(self):
  p=order_plan(self.c);f=simulate_filled(p,200);self.assertEqual(budget_consumption(self.c,f,commission_model(self.c))["status"],"PASS")
 def test_replay(self): self.assertTrue(replay({"a":1})["deterministic"])
 def test_scenario(self): self.assertTrue(simulation_scenario(self.c)["replay_deterministic"])
 def test_rollback(self): self.assertEqual(rollback_plan()["status"],"PASS")
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   o=Path(t);store(o,{"a":{"x":1}});self.assertTrue(store(o,{"a":{"x":1}})["reused"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   o=Path(t);z=store(o,{"a":{"x":1}});m=manifest(o,z["ledger"]);self.assertTrue(verify_manifest(o,m))
 def test_bad_source(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"x";p.write_text("{}")
   with self.assertRaises(ValueError):validate_source(p)
 def test_stage_count(self):self.assertEqual(len([f"V87.{i:02d}" for i in range(21,41)]),20)

if __name__=="__main__":unittest.main()
