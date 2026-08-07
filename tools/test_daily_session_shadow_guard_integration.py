import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from paper_daily_session.shadow_integration import DailySessionShadowGuard


class FakeClient:
    def get_all_positions(self):
        return [
            SimpleNamespace(
                symbol="AAPL",
                market_value="647.69",
                qty="2.08",
                unrealized_pl="15",
            )
        ]


class Tests(unittest.TestCase):
    def _root(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)

        policy = root / "config/smart_safe_guard_policy.json"
        policy.parent.mkdir(parents=True, exist_ok=True)
        policy.write_text(json.dumps({
            "mode": "SHADOW",
            "minimum_confidence": 0.8,
            "minimum_consensus_score": 0.75,
            "minimum_reward_risk": 1.5,
            "maximum_order_notional": 100,
            "maximum_daily_orders": 1,
            "maximum_open_positions": 2,
            "maximum_daily_loss": 50,
            "maximum_consecutive_losses": 2,
            "maximum_symbol_exposure": 500,
            "minimum_minutes_to_close": 15,
            "block_duplicate_symbol_buy": True,
            "live_write_enabled": False
        }), encoding="utf-8")

        candidate = root / "release/v14001_15000_paper_autonomous_execution/actual/latest_paper_execution_cycle.json"
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text(json.dumps({
            "selected_candidate": {
                "symbol": "AAPL",
                "side": "buy",
                "confidence": 0.91,
                "consensus_score": 0.90,
                "reward_risk": 2.0,
                "quantity": 0.08,
                "reference_price": 311.45
            }
        }), encoding="utf-8")
        return temp, root

    def test_shadow_integration_records_actual_safety_reasons(self):
        temp, root = self._root()
        try:
            account = SimpleNamespace(
                status="ACTIVE",
                trading_blocked=False,
                buying_power="10000",
                equity="100000",
                last_equity="100000",
            )
            result = DailySessionShadowGuard(root).evaluate(
                client=FakeClient(),
                account=account,
                clock={"market_open": True, "minutes_to_close": 120},
                today_order_count=1,
            )
            self.assertEqual(result["mode"], "SHADOW")
            self.assertFalse(result["enforced"])
            self.assertIn("DAILY_ORDER_LIMIT", result["issue_codes"])
            self.assertIn("DUPLICATE_SYMBOL_BUY", result["issue_codes"])
        finally:
            temp.cleanup()

    def test_shadow_decision_file_is_written(self):
        temp, root = self._root()
        try:
            account = SimpleNamespace(
                status="ACTIVE",
                trading_blocked=False,
                buying_power="10000",
                equity="100000",
                last_equity="100000",
            )
            DailySessionShadowGuard(root).evaluate(
                client=FakeClient(),
                account=account,
                clock={"market_open": True, "minutes_to_close": 120},
                today_order_count=0,
            )
            self.assertTrue(
                (root / "runtime/paper_autonomous_daily_session/latest_shadow_guard_decision.json").exists()
            )
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
