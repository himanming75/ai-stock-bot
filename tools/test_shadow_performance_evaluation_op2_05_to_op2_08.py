import json
import tempfile
import unittest
from pathlib import Path

from autonomous_paper_runtime.shadow_performance_evaluation import (
    ShadowPerformanceEvaluation,
)


class Tests(unittest.TestCase):
    def write(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def data(self):
        source = {
            "status": "PASS",
            "state": "SHADOW_DECISION_READY",
            "shadow_decision_ready": True,
            "shadow_session_id": "shadow-session-001",
            "safe_mode_engaged": False,
        }
        policy = {
            "evaluation_id": "evaluation-001",
            "shadow_only": True,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "minimum_completed_trades": 2,
            "initial_shadow_capital": 100000,
            "maximum_drawdown_limit_pct": 5,
            "minimum_profit_factor": 1,
        }
        evidence = {
            "trades": [
                {
                    "decision_id": "d1",
                    "symbol": "AAPL",
                    "action": "BUY",
                    "entry_price": 100,
                    "exit_price": 110,
                    "quantity": 2,
                    "fees": 0,
                },
                {
                    "decision_id": "d2",
                    "symbol": "MSFT",
                    "action": "BUY",
                    "entry_price": 100,
                    "exit_price": 95,
                    "quantity": 1,
                    "fees": 0,
                },
            ]
        }
        return source, policy, evidence

    def run_case(self, values):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        names = ["source", "policy", "evidence"]
        paths = {name: root/f"{name}.json" for name in names}
        for name, value in zip(names, values):
            if value is not None:
                self.write(paths[name], value)

        result = ShadowPerformanceEvaluation().run(
            shadow_result_path=paths["source"],
            evaluation_policy_path=paths["policy"],
            trade_evidence_path=paths["evidence"],
            trade_metrics_path=root/"metrics.json",
            equity_curve_path=root/"curve.json",
            performance_report_path=root/"report.json",
            evaluation_token_path=root/"token.json",
            result_path=root/"result.json",
        )
        return result, root

    def test_wait_before_shadow_ready(self):
        source, policy, evidence = self.data()
        source = {
            "status": "PASS",
            "state": "WAIT_WINDOWS_SCHEDULED_COLLECTION",
            "shadow_decision_ready": False,
            "safe_mode_engaged": False,
        }
        result, _ = self.run_case((source, policy, evidence))
        self.assertEqual(result["state"], "WAIT_SHADOW_DECISION")

    def test_performance_ready(self):
        result, root = self.run_case(self.data())
        self.assertEqual(
            result["state"],
            "SHADOW_PERFORMANCE_EVALUATION_READY",
        )
        self.assertEqual(result["completed_trade_count"], 2)
        self.assertEqual(result["wins"], 1)
        self.assertEqual(result["losses"], 1)
        self.assertTrue(result["performance_approved"])
        self.assertTrue((root/"token.json").exists())

    def test_insufficient_trades_blocks(self):
        source, policy, evidence = self.data()
        evidence = {"trades": evidence["trades"][:1]}
        result, _ = self.run_case((source, policy, evidence))
        self.assertEqual(result["status"], "BLOCKED")

    def test_sell_trade_calculation(self):
        source, policy, _ = self.data()
        policy = dict(policy)
        policy["minimum_completed_trades"] = 1
        evidence = {
            "trades": [{
                "decision_id": "d1",
                "symbol": "TSLA",
                "action": "SELL",
                "entry_price": 100,
                "exit_price": 90,
                "quantity": 2,
                "fees": 0,
            }]
        }
        result, _ = self.run_case((source, policy, evidence))
        self.assertEqual(result["total_pnl"], 20)
        self.assertEqual(result["wins"], 1)

    def test_drawdown_can_hold_performance(self):
        source, policy, evidence = self.data()
        policy = dict(policy)
        policy["initial_shadow_capital"] = 100
        policy["maximum_drawdown_limit_pct"] = 1
        result, _ = self.run_case((source, policy, evidence))
        self.assertFalse(result["performance_approved"])

    def test_submission_policy_blocks(self):
        source, policy, evidence = self.data()
        policy = dict(policy)
        policy["order_submission_enabled"] = True
        result, _ = self.run_case((source, policy, evidence))
        self.assertEqual(result["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
