import unittest

from dashboard.panels import (
    build_dashboard_payload,
    daily_report_panel,
    portfolio_panel,
    runtime_panel,
    signal_panel,
)


class Tests(unittest.TestCase):
    def test_missing_data_is_safe(self):
        payload = build_dashboard_payload({})
        self.assertEqual(payload["dashboard_state"], "READY")
        self.assertEqual(payload["runtime"]["state"], "NO_RUNTIME_DATA")
        self.assertFalse(payload["order_submission_enabled"])

    def test_runtime_panel(self):
        panel = runtime_panel({
            "runtime": {
                "state": "SHADOW_DAILY_AUTOMATION_READY",
                "status": "PASS",
                "runtime_id": "runtime-1",
                "safe_mode_engaged": False,
            }
        })
        self.assertEqual(panel["runtime_id"], "runtime-1")
        self.assertEqual(panel["status"], "PASS")

    def test_safe_mode_is_visible(self):
        payload = build_dashboard_payload({
            "runtime": {"safe_mode_engaged": True}
        })
        self.assertEqual(payload["dashboard_state"], "SAFE_MODE")

    def test_portfolio_values(self):
        panel = portfolio_panel({
            "portfolio": {
                "account": {
                    "status": "ACTIVE",
                    "cash": "100000",
                    "buying_power": "200000",
                    "portfolio_value": "101000",
                    "equity": "101000",
                },
                "open_orders": [{"id": "1"}],
                "positions": [{"symbol": "AAPL"}],
            }
        })
        self.assertEqual(panel["cash"], 100000)
        self.assertEqual(panel["position_count"], 1)

    def test_shadow_signal_panel(self):
        panel = signal_panel({
            "signal": {
                "symbol": "AAPL",
                "requested_action": "BUY",
                "approved_action": "HOLD",
                "confidence": 0.6,
                "pipeline_reasons": ["CONFIDENCE_BELOW_MINIMUM"],
            }
        })
        self.assertEqual(panel["approved_action"], "HOLD")
        self.assertIn("CONFIDENCE_BELOW_MINIMUM", panel["reasons"])

    def test_daily_report_panel(self):
        panel = daily_report_panel({
            "daily_report": {
                "signal_count": 3,
                "buy_count": 1,
                "sell_count": 1,
                "hold_count": 1,
                "total_pnl": 12.5,
                "daily_shadow_report_ready": True,
            }
        })
        self.assertEqual(panel["signal_count"], 3)
        self.assertEqual(panel["total_pnl"], 12.5)
        self.assertTrue(panel["report_ready"])


if __name__ == "__main__":
    unittest.main()
