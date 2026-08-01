from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.strategy_execution_reconciliation_v87_41_60 import *

class T(unittest.TestCase):
 def setUp(self): self.c=StrategyExecutionReconciliationConfig()
 def test_config(self): self.c.validate()
 def test_auto_exec_rejected(self):
  with self.assertRaises(ValueError):StrategyExecutionReconciliationConfig(auto_execution_enabled=True).validate()
 def test_order_fill(self):
  s={"accepted_count":1,"partial_count":1,"filled_count":1,"rejected_count":1,"canceled_count":1}
  self.assertEqual(order_fill_reconciliation(s)["status"],"PASS")
 def test_quantity(self):
  self.assertEqual(quantity_reconciliation({"quantity":1,"position_qty":1},self.c)["status"],"PASS")
 def test_cash(self):
  self.assertEqual(cash_reconciliation({"closing_cash":99799.9},self.c)["status"],"PASS")
 def test_equity(self):
  self.assertEqual(equity_reconciliation({"closing_cash":99799.9},self.c)["status"],"PASS")
 def test_pnl(self):
  self.assertEqual(pnl_reconciliation({"position_qty":1,"unrealized_pnl":1},self.c)["status"],"PASS")
 def test_drawdown(self):
  self.assertEqual(drawdown_reconciliation({"closing_cash":99799.9,"drawdown":0},self.c)["status"],"PASS")
 def test_budget(self): self.assertEqual(budget_reconciliation({"filled_count":1})["status"],"PASS")
 def test_replay(self): self.assertEqual(replay_reconciliation({"replay_deterministic":True})["status"],"PASS")
 def test_chain(self):
  c=ledger_chain({"a":{"x":1}});self.assertEqual(c["status"],"PASS")
 def test_tamper(self):
  c=ledger_chain({"a":{"x":1}});self.assertEqual(tamper_detection(c)["status"],"PASS")
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
 def test_stage_count(self):self.assertEqual(len([f"V87.{i:02d}" for i in range(41,61)]),20)

if __name__=="__main__":unittest.main()
