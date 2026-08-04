import tempfile,unittest
from pathlib import Path
from ai_strategy_ensemble.config import load,validate
from ai_strategy_ensemble.scoring import score
from ai_strategy_ensemble.ranking import rank
from ai_strategy_ensemble.allocation import allocate
from ai_strategy_ensemble.signal import combine
from ai_strategy_ensemble.engine import evaluate

ROWS=[
{"strategy_id":"A","observations":20,"win_rate_pct":60,"profit_factor":1.8,"sharpe":1.2,"maximum_drawdown_pct":3,"total_pnl":500},
{"strategy_id":"B","observations":20,"win_rate_pct":50,"profit_factor":1.2,"sharpe":0.7,"maximum_drawdown_pct":5,"total_pnl":200},
]

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:self.assertFalse(load(Path(t))["automatic_order_submission_enabled"])
    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:self.assertTrue(validate(load(Path(t)))["valid"])
    def test_score(self):
        with tempfile.TemporaryDirectory() as t:self.assertGreater(score(ROWS[0],load(Path(t)))["score"],0)
    def test_rank(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(rank(ROWS,load(Path(t)))[0]["strategy_id"],"A")
    def test_allocate(self):
        with tempfile.TemporaryDirectory() as t:self.assertGreater(len(allocate(rank(ROWS,load(Path(t))),load(Path(t)))),0)
    def test_signal(self):
        result=combine([{"strategy_id":"A","symbol":"AAPL","action":"BUY","confidence":1}], [{"strategy_id":"A","weight_pct":100}])
        self.assertEqual(result["signals"][0]["action"],"BUY")
    def test_engine_live_zero(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(evaluate(Path(t))["actual_live_orders_submitted"],0)

if __name__=="__main__":unittest.main()
