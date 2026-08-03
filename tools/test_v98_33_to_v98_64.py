import tempfile,unittest
from pathlib import Path
from backtest_batch.queue import build_batch_jobs,pending_jobs
from backtest_batch.executor import execute_job
from backtest_batch.retry import execute_with_retry
from backtest_batch.regression import evaluate_regression
from backtest_batch.champion import select_champion
from backtest_batch.engine import evaluate

class Tests(unittest.TestCase):
    def test_queue(self):
        jobs=build_batch_jobs(
            [{"state":"COMPLETED","job_id":"a","strategy_id":"S","symbol":"AAPL","window_id":"W","total_return_pct":10,"maximum_drawdown_pct":2,"win_rate_pct":50}],
            [{"scenario_id":"BASE"}],
        )
        self.assertEqual(len(jobs),1)

    def test_pending(self):
        jobs=[{"batch_job_id":"a"},{"batch_job_id":"b"}]
        self.assertEqual(len(pending_jobs(jobs,{"completed_job_ids":["a"]})),1)

    def test_execute(self):
        row=execute_job({
            "base_return_pct":10,"return_shock_pct":-2,
            "base_drawdown_pct":3,"drawdown_shock_pct":1,
            "base_win_rate_pct":50,
        },{})
        self.assertEqual(row["adjusted_return_pct"],8)

    def test_retry(self):
        calls={"n":0}
        def runner(job):
            calls["n"]+=1
            if calls["n"]==1: raise ValueError("x")
            return {"state":"COMPLETED","status":"PASS"}
        result=execute_with_retry({},runner,1)
        self.assertEqual(result["attempt_count"],2)

    def test_regression(self):
        self.assertTrue(evaluate_regression({
            "adjusted_return_pct":5,
            "adjusted_drawdown_pct":2,
            "regression_score":3,
        },{"minimum_adjusted_return_pct":0,"maximum_adjusted_drawdown_pct":10,"minimum_regression_score":0})["passed"])

    def test_champion(self):
        result=select_champion([{
            "state":"COMPLETED","strategy_id":"A",
            "regression_score":5,"adjusted_return_pct":6,
            "adjusted_drawdown_pct":2,
            "regression_gate":{"passed":True},
        }])
        self.assertEqual(result["strategy_id"],"A")

    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["state"],"BACKTEST_BATCH_SOURCE_REQUIRED")

    def test_safety(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(evaluate(Path(t))["order_submission_enabled"])

if __name__=="__main__": unittest.main()
