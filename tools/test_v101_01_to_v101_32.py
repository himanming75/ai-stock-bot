import tempfile,unittest
from pathlib import Path
from portfolio_rebalance_control.core import drift_rows,adjustments,controls,evaluate
class Tests(unittest.TestCase):
 def test_drift(self): self.assertEqual([x for x in drift_rows([{'strategy_id':'A','target_weight_pct':40}],[{'strategy_id':'A','current_weight_pct':30}],10,20,{}) if x['strategy_id']=='A'][0]['drift_pct'],-10)
 def test_zone(self): self.assertEqual(drift_rows([{'strategy_id':'A','target_weight_pct':40}],[{'strategy_id':'A','current_weight_pct':44}],10,6,{'rebalance_trigger_pct':3})[0]['drift_zone'],'REBALANCE')
 def test_adjustment(self): self.assertEqual(adjustments([{'strategy_id':'A','drift_pct':-10,'drift_zone':'CRITICAL','rebalance_required':True}],100000,{'incremental_rebalance_fraction':.5})[0]['planned_notional'],5000)
 def test_controls(self):
  v=controls([{'strategy_id':'A','side':'BUY','drift_pct':-10,'planned_notional':5000,'submission_allowed':False,'state':'PLANNED'}],100000,12000,{'minimum_cash_pct':10,'maximum_turnover_pct':20});self.assertEqual(v['projected_cash_pct'],10)
 def test_safety(self):
  with tempfile.TemporaryDirectory() as t:self.assertFalse(evaluate(Path(t))['order_submission_enabled'])
 def test_missing(self):
  with tempfile.TemporaryDirectory() as t:self.assertEqual(evaluate(Path(t))['state'],'PORTFOLIO_REBALANCE_CONTROL_SOURCE_REQUIRED')
if __name__=='__main__':unittest.main()
