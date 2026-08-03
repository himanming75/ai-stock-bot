import csv, tempfile, unittest
from pathlib import Path
from automated_backtest.discovery import discover_strategies
from automated_backtest.matrix import build_matrix
from automated_backtest.data import load_bars, slice_bars
from automated_backtest.strategies import signals
from automated_backtest.runner import maximum_drawdown, run_job
from automated_backtest.aggregation import score_result, aggregate
from automated_backtest.engine import evaluate

class Tests(unittest.TestCase):
    def test_discovery(self):
        rows=discover_strategies({"strategies":[{"strategy_id":"A","family":"BUY_HOLD"}]})
        self.assertEqual(len(rows),1)

    def test_matrix(self):
        jobs=build_matrix(
            [{"strategy_id":"A","family":"BUY_HOLD","parameters":{}}],
            [{"dataset_id":"D","symbol":"AAPL","path":"x","exists":True}],
            [{"window_id":"W","start_index":0,"end_index":10}],
        )
        self.assertEqual(len(jobs),1)

    def test_data(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/"x.csv"
            path.write_text("close\n100\n101\n",encoding="utf-8")
            self.assertEqual(len(load_bars(path)),2)
            self.assertEqual(len(slice_bars(load_bars(path),0,1)),1)

    def test_signals(self):
        self.assertEqual(signals("BUY_HOLD",[1,2,3],{}),[1,1,1])
        self.assertEqual(len(signals("MOMENTUM",[1,2,3],{"period":1})),3)

    def test_drawdown(self):
        self.assertAlmostEqual(maximum_drawdown([100,110,99]),10.0)

    def test_run_job(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/"x.csv"
            path.write_text(
                "close\n" + "\n".join(str(100+i) for i in range(40)) + "\n",
                encoding="utf-8",
            )
            job={
                "job_id":"1","strategy_id":"A","family":"BUY_HOLD",
                "parameters":{},"dataset_id":"D","symbol":"AAPL",
                "dataset_path":str(path),"dataset_exists":True,
                "window_id":"W","start_index":0,"end_index":40,
            }
            self.assertEqual(run_job(job,{"minimum_bars":30})["state"],"COMPLETED")

    def test_score(self):
        self.assertGreater(
            score_result({
                "state":"COMPLETED","total_return_pct":10,
                "maximum_drawdown_pct":1,"win_rate_pct":50
            }),0
        )

    def test_aggregate(self):
        value=aggregate([{
            "state":"COMPLETED","status":"PASS",
            "total_return_pct":1,"maximum_drawdown_pct":0,
            "win_rate_pct":50
        }])
        self.assertEqual(value["completed_count"],1)

    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(
                evaluate(Path(t))["state"],
                "AUTOMATED_BACKTEST_SOURCE_REQUIRED",
            )

    def test_safety(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(evaluate(Path(t))["order_submission_enabled"])

if __name__=="__main__":
    unittest.main()
