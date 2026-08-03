import json, tempfile, unittest
from pathlib import Path
from v89_engine.io import normalize_bar, load_bars
from v89_engine.backtest import run_strategy, buy_hold
from v89_engine.gates import evaluate
from v89_engine.discovery import discover_historical_files
from v89_engine.final_validation import status

def bars(n=120):
 out=[]; c=100
 for i in range(n):
  c += .8 if i%30<18 else -.5
  out.append({"timestamp":f"2026-{i:03d}","open":c-.2,"high":c+.5,"low":c-.5,"close":c,"volume":1000})
 return out

class Tests(unittest.TestCase):
 def test_normalize(self): self.assertEqual(normalize_bar({"t":"x","o":1,"h":2,"l":.5,"c":1.5})["close"],1.5)
 def test_backtest(self): self.assertIn("total_return_pct",run_strategy(bars(),"EMA_CROSS",{"fast":5,"slow":15}))
 def test_benchmark(self): self.assertEqual(buy_hold(bars())["total_trades"],1)
 def test_gate(self): self.assertIn("approved",evaluate({"total_trades":3,"profit_factor":2,"maximum_drawdown_pct":5,"sharpe_ratio":1,"total_return_pct":10},{},5))
 def test_discovery(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/"historical/a.json"; p.parent.mkdir(); p.write_text(json.dumps({"bars":bars()}))
   self.assertEqual(discover_historical_files(Path(t))["candidate_count"],1)
 def test_final_wait(self):
  with tempfile.TemporaryDirectory() as t: self.assertEqual(status(Path(t))["remaining_days"],3)
 def test_final_ready(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/"release/v83_77_to_v83_80/actual/multi_day_paper_validation_result.json"; p.parent.mkdir(parents=True)
   p.write_text('{"completed_days":3,"minimum_days":3}')
   self.assertTrue(status(Path(t))["requirement_met"])
 def test_safety(self):
  from v89_engine.engine import run
  with tempfile.TemporaryDirectory() as t: self.assertFalse(run(Path(t))["order_submission_enabled"])
if __name__=="__main__": unittest.main()
