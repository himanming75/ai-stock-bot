import tempfile, unittest
from pathlib import Path
from parameter_optimizer.search_space import get_space
from parameter_optimizer.walk_forward import split_windows, evaluate_windows
from parameter_optimizer.scoring import optimization_score, stability_gate
from parameter_optimizer.engine import candidate_strategy_ids, optimize

def bars(n=240):
    out=[]
    close=100.0
    for i in range(n):
        close += 0.7 if i%40<24 else -0.45
        out.append({
            "timestamp":f"2026-{i:03d}",
            "open":close-.2,
            "high":close+.5,
            "low":close-.5,
            "close":close,
            "volume":1000+i,
        })
    return out

class Tests(unittest.TestCase):
    def test_ema_space(self):
        self.assertGreater(len(get_space("EMA_CROSS")),10)
    def test_rsi_space(self):
        self.assertGreater(len(get_space("RSI")),10)
    def test_windows(self):
        self.assertEqual(len(split_windows(bars(),4)),4)
    def test_walk_forward(self):
        result=evaluate_windows(bars(),"MOMENTUM",{"period":10},4)
        self.assertEqual(result["window_count"],4)
    def test_score(self):
        full={"total_return_pct":10,"maximum_drawdown_pct":5,"sharpe_ratio":1}
        walk={"positive_window_pct":75,"average_return_pct":2,"worst_return_pct":-1,"worst_drawdown_pct":4}
        self.assertIsInstance(optimization_score(full,walk),float)
    def test_gate(self):
        full={"total_trades":5,"sharpe_ratio":1}
        walk={"positive_window_pct":75,"average_return_pct":2,"worst_drawdown_pct":10}
        self.assertTrue(stability_gate(full,walk,{})["passed"])
    def test_candidate_ids(self):
        source={"rankings":[{"strategy_id":"MOMENTUM_10"}]}
        self.assertEqual(candidate_strategy_ids(source,1),["MOMENTUM_10"])
    def test_missing_data_state(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(
                optimize(Path(t))["state"],
                "PARAMETER_OPTIMIZATION_HISTORICAL_DATA_REQUIRED",
            )
    def test_safety(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(optimize(Path(t))["order_submission_enabled"])
    def test_unknown_space(self):
        self.assertEqual(get_space("UNKNOWN"),[])

if __name__=="__main__":
    unittest.main()
