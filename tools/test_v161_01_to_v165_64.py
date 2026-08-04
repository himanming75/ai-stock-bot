import tempfile,unittest
from pathlib import Path
from paper_qualification.metrics import compute
from paper_qualification.strategies import analyze,score
from paper_qualification.windows import evaluate
from paper_qualification.config import load,validate
from paper_qualification.engine import evaluate as run

TRADES=[{"realized_pnl":10,"strategy_id":"M","session_date":"2026-01-01"},{"realized_pnl":-5,"strategy_id":"M","session_date":"2026-01-02"}]
DAILY=[{"session_date":"2026-01-01","daily_return_pct":1,"ending_equity":1010},{"session_date":"2026-01-02","daily_return_pct":-0.5,"ending_equity":1005}]

class Tests(unittest.TestCase):
    def test_metrics(self):self.assertEqual(compute(TRADES,DAILY)["profit_factor"],2)
    def test_strategy(self):self.assertEqual(analyze(TRADES,DAILY)[0]["strategy_id"],"M")
    def test_score(self):self.assertGreaterEqual(score(compute(TRADES,DAILY)),0)
    def test_windows(self):self.assertIn("5",evaluate(DAILY,TRADES))
    def test_policy(self):
        with tempfile.TemporaryDirectory() as t:self.assertTrue(validate(load(Path(t)))["valid"])
    def test_live_zero(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(run(Path(t))["actual_live_orders_submitted"],0)
    def test_empty_in_progress(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(run(Path(t))["state"],"PAPER_QUALIFICATION_IN_PROGRESS")

if __name__=="__main__":unittest.main()
