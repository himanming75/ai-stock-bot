import tempfile,unittest
from pathlib import Path

from autonomous_paper_operations.tournament import (
    score_strategy,run_tournament
)
from autonomous_paper_operations.sessions import build_sessions
from autonomous_paper_operations.scenario import scenario_for_session
from autonomous_paper_operations.recovery import execute_with_retry
from autonomous_paper_operations.report import build_operations_report
from autonomous_paper_operations.engine import evaluate

class Tests(unittest.TestCase):
    def test_score(self):
        self.assertGreater(score_strategy({
            "return_pct":10,
            "max_drawdown_pct":5,
            "win_rate_pct":60,
            "sharpe":1,
        }),0)

    def test_tournament(self):
        value=run_tournament([
            {"strategy_id":"A","return_pct":10},
            {"strategy_id":"B","return_pct":5},
        ])
        self.assertEqual(value["champion"]["strategy_id"],"A")

    def test_sessions_skip_weekend(self):
        rows=build_sessions("2026-08-07",3)
        self.assertEqual(rows[1]["session_date"],"2026-08-10")

    def test_scenario(self):
        value=scenario_for_session({"SPY":100},1)
        self.assertIn("SPY",value["closing_prices"])

    def test_retry(self):
        value=execute_with_retry(lambda:{"ok":True},3)
        self.assertTrue(value["passed"])
        self.assertEqual(value["attempt_count"],1)

    def test_report(self):
        value=build_operations_report(
            [{
                "state":"COMPLETED",
                "ending_equity":101000,
            }],
            {"champion":{"strategy_id":"A"}},
            100000,
        )
        self.assertEqual(value["cumulative_pnl"],1000)

    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as temp:
            result=evaluate(Path(temp))
            self.assertEqual(
                result["state"],
                "AUTONOMOUS_PAPER_OPERATIONS_SOURCE_REQUIRED",
            )

    def test_orders_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(
                evaluate(Path(temp))["actual_orders_submitted"],
                0,
            )

    def test_live_disabled(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertFalse(
                evaluate(Path(temp))["live_trading_enabled"]
            )

if __name__=="__main__":
    unittest.main()
