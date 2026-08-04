import tempfile,unittest
from pathlib import Path
from multi_account_engine.config import load,validate
from multi_account_engine.credentials import detect
from multi_account_engine.routing import route
from multi_account_engine.risk import evaluate
from multi_account_engine.conflicts import resolve
from multi_account_engine.engine import evaluate as engine
class Tests(unittest.TestCase):
 def test_policy_safe(self):
  p=load(Path(tempfile.mkdtemp())); self.assertFalse(p["paper_submission_enabled"]); self.assertFalse(p["live_submission_enabled"])
 def test_validate(self): self.assertTrue(validate(load(Path(tempfile.mkdtemp())))["valid"])
 def test_credentials_missing(self): self.assertFalse(detect({"credential_prefix":"NOT_REAL"})["ready"])
 def test_routing(self): self.assertEqual(route([{"strategy_id":"s","profile":"SCALP","eligible":True}],[{"account_id":"A","enabled":True,"assigned_profiles":["SCALP"]}])[0]["account_id"],"A")
 def test_kill_switch_blocks(self):
  a={"account_id":"A","kill_switch_enabled":True,"daily_loss_limit_pct":1,"maximum_drawdown_pct":5,"maximum_positions":2,"maximum_orders_per_day":2,"capital_limit":1000}; self.assertFalse(evaluate(a,{"equity":900,"peak_equity":1000})["passed"])
 def test_conflict(self): self.assertEqual(len([x for x in resolve([{"symbol":"A","strategy_score":90},{"symbol":"A","strategy_score":80}],False) if x["route_allowed"]]),1)
 def test_engine_zero_orders(self):
  r=engine(Path(tempfile.mkdtemp())); self.assertEqual(r["actual_paper_orders_submitted"],0); self.assertEqual(r["actual_live_orders_submitted"],0)
if __name__=="__main__": unittest.main()
