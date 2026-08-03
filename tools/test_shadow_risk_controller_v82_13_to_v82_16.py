
import json
import tempfile
import unittest
from pathlib import Path

from shadow_runtime.risk_controller_v82_13_16 import (
    evaluate_risk,
    run_shadow_risk_controller,
)


class Tests(unittest.TestCase):
    def base_policy(self):
        return {
            "shadow_only": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "order_submission_enabled": False,
            "maximum_daily_loss": 500,
            "maximum_drawdown_pct": 5,
            "maximum_gross_exposure_pct": 100,
            "maximum_symbol_exposure_pct": 35,
            "maximum_daily_trades": 10,
            "maximum_consecutive_losses": 3,
        }

    def test_daily_loss_trigger(self):
        policy = self.base_policy()
        policy["daily_realized_pnl_override"] = -500
        result = evaluate_risk(
            analytics={},
            portfolio={},
            policy=policy,
        )
        self.assertIn(
            "MAXIMUM_DAILY_LOSS_EXCEEDED",
            result["risk_reasons"],
        )

    def test_drawdown_trigger(self):
        result = evaluate_risk(
            analytics={"maximum_drawdown_pct": 5},
            portfolio={},
            policy=self.base_policy(),
        )
        self.assertIn(
            "MAXIMUM_DRAWDOWN_EXCEEDED",
            result["risk_reasons"],
        )

    def test_exposure_trigger(self):
        result = evaluate_risk(
            analytics={},
            portfolio={
                "gross_exposure_pct": 100,
                "symbol_exposures_pct": {"AAPL": 40},
            },
            policy=self.base_policy(),
        )
        self.assertTrue(result["emergency_stop_required"])

    def test_trade_limit_trigger(self):
        policy = self.base_policy()
        policy["daily_trade_count_override"] = 10
        result = evaluate_risk(
            analytics={},
            portfolio={},
            policy=policy,
        )
        self.assertIn(
            "MAXIMUM_DAILY_TRADES_EXCEEDED",
            result["risk_reasons"],
        )

    def test_consecutive_loss_trigger(self):
        policy = self.base_policy()
        policy["consecutive_losses_override"] = 3
        result = evaluate_risk(
            analytics={},
            portfolio={},
            policy=policy,
        )
        self.assertIn(
            "MAXIMUM_CONSECUTIVE_LOSSES_EXCEEDED",
            result["risk_reasons"],
        )

    def write(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def run_case(
        self,
        *,
        emergency=False,
        recovery=False,
        existing_active=False,
        policy_updates=None,
    ):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)

        policy = self.base_policy()
        if policy_updates:
            policy.update(policy_updates)

        self.write(root / "analytics.json", {
            "cumulative_pnl": 0,
            "maximum_drawdown_pct": 0,
            "trade_count": 0,
        })
        self.write(root / "portfolio.json", {
            "gross_exposure_pct": 0,
            "symbol_exposures_pct": {},
        })
        self.write(root / "policy.json", policy)
        if existing_active:
            self.write(root / "kill.json", {"active": True})

        result = run_shadow_risk_controller(
            analytics_result_path=root / "analytics.json",
            portfolio_state_path=root / "portfolio.json",
            policy_path=root / "policy.json",
            kill_switch_path=root / "kill.json",
            recovery_lock_path=root / "recovery.json",
            risk_report_path=root / "report.json",
            dashboard_path=root / "dashboard.json",
            result_path=root / "result.json",
            emergency_stop_requested=emergency,
            recovery_requested=recovery,
        )
        return result, root

    def test_risk_clear(self):
        result, _ = self.run_case()
        self.assertEqual(result["state"], "SHADOW_RISK_CLEAR")

    def test_manual_emergency_stop(self):
        result, _ = self.run_case(emergency=True)
        self.assertTrue(result["kill_switch_active"])
        self.assertEqual(
            result["state"],
            "SHADOW_RISK_KILL_SWITCH_ACTIVE",
        )

    def test_recovery_unlock(self):
        result, _ = self.run_case(
            recovery=True,
            existing_active=True,
        )
        self.assertFalse(result["kill_switch_active"])
        self.assertEqual(result["state"], "SHADOW_RISK_CLEAR")

    def test_outputs_written(self):
        result, root = self.run_case()
        self.assertTrue(result["kill_switch_written"])
        self.assertTrue((root / "kill.json").exists())
        self.assertTrue((root / "dashboard.json").exists())

    def test_read_only_contract(self):
        result, _ = self.run_case()
        self.assertFalse(result["broker_write_enabled"])
        self.assertFalse(result["order_submission_enabled"])
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["write_requests_executed"], 0)
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
