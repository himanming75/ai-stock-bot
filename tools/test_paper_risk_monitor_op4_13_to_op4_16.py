import json
import tempfile
import unittest
from pathlib import Path

from paper_pilot.risk_monitor import PaperPilotRiskMonitor


class Tests(unittest.TestCase):
    def write(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def data(self):
        policy = {
            "paper_only": True,
            "read_only": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "maximum_drawdown_pct": 5,
            "maximum_daily_loss_pct": 3,
            "maximum_gross_exposure_pct": 100,
            "maximum_symbol_exposure_pct": 50,
        }
        foundation = {
            "pilot_started": True,
            "pilot_id": "pilot-1",
            "session_id": "session-1",
        }
        session = {
            "health_status": "HEALTHY",
            "timeout_detected": False,
            "controlled_stop_required": False,
        }
        performance = {
            "initial_equity": 100000,
            "latest_equity": 99000,
            "max_drawdown_pct": 1,
            "cumulative_return_pct": -1,
        }
        snapshot = {
            "snapshot_type": "ACTUAL_ALPACA_PAPER_READ_ONLY",
            "paper_only": True,
            "read_only": True,
            "account": {
                "equity": "99000",
                "portfolio_value": "99000",
                "cash": "70000",
            },
            "positions": [{
                "symbol": "AAPL",
                "market_value": "29000",
            }],
        }
        return policy, foundation, session, performance, snapshot

    def run_case(self, values):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        names = ["policy", "foundation", "session", "performance", "snapshot"]
        paths = {name: root/f"{name}.json" for name in names}
        for name, value in zip(names, values):
            self.write(paths[name], value)

        result = PaperPilotRiskMonitor().run(
            policy_path=paths["policy"],
            foundation_result_path=paths["foundation"],
            session_monitor_result_path=paths["session"],
            performance_result_path=paths["performance"],
            current_snapshot_path=paths["snapshot"],
            drawdown_report_path=root/"drawdown.json",
            exposure_report_path=root/"exposure.json",
            daily_loss_report_path=root/"daily.json",
            emergency_stop_gate_path=root/"stop.json",
            dashboard_state_path=root/"dashboard.json",
            result_path=root/"result.json",
            observed_at="2026-08-02T08:00:00+00:00",
        )
        return result, root

    def test_healthy_risk(self):
        result, _ = self.run_case(self.data())
        self.assertEqual(result["state"], "PAPER_RISK_HEALTHY")
        self.assertFalse(result["emergency_stop_required"])

    def test_drawdown_triggers_stop(self):
        values = list(self.data())
        values[3] = dict(values[3])
        values[3]["max_drawdown_pct"] = 6
        result, _ = self.run_case(tuple(values))
        self.assertEqual(result["state"], "EMERGENCY_STOP_REQUIRED")
        self.assertIn("MAX_DRAWDOWN_EXCEEDED", result["risk_reasons"])

    def test_daily_loss_triggers_stop(self):
        values = list(self.data())
        values[3] = dict(values[3])
        values[3]["cumulative_return_pct"] = -4
        result, _ = self.run_case(tuple(values))
        self.assertIn("MAX_DAILY_LOSS_EXCEEDED", result["risk_reasons"])

    def test_symbol_exposure_triggers_stop(self):
        values = list(self.data())
        values[4] = dict(values[4])
        values[4]["positions"] = [{
            "symbol": "AAPL",
            "market_value": "60000",
        }]
        result, _ = self.run_case(tuple(values))
        self.assertIn("MAX_SYMBOL_EXPOSURE_EXCEEDED", result["risk_reasons"])

    def test_wait_before_pilot_start(self):
        values = list(self.data())
        values[1] = {"pilot_started": False}
        result, _ = self.run_case(tuple(values))
        self.assertEqual(result["state"], "WAIT_PILOT_START")
        self.assertFalse(result["emergency_stop_required"])

    def test_read_only_contract(self):
        result, _ = self.run_case(self.data())
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["write_requests_executed"], 0)
        self.assertFalse(result["broker_write_enabled"])
        self.assertFalse(result["cancel_enabled"])
        self.assertFalse(result["position_close_enabled"])


if __name__ == "__main__":
    unittest.main()
