import json, tempfile, unittest
from pathlib import Path

from autonomous_paper_runtime.daily_read_only_observation import DailyReadOnlyObservation


class Tests(unittest.TestCase):
    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def data(self):
        pilot = {
            "status": "PASS",
            "state": "PAPER_OPERATIONS_READ_ONLY_READY",
            "paper_operations_pilot_ready": True,
            "pilot_id": "pilot-001",
            "safe_mode_engaged": False,
        }
        policy = {
            "observation_id": "observation-001",
            "read_only": True,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "max_allowed_open_orders": 0,
            "max_allowed_positions": 0,
            "max_abs_equity_drift": 1000,
            "max_abs_cash_drift": 1000,
        }
        previous = {
            "account": {
                "status": "ACTIVE",
                "account_blocked": False,
                "trading_blocked": False,
                "equity": "100000",
                "cash": "100000",
            },
            "clock": {"is_open": False},
            "open_orders": [],
            "positions": [],
        }
        current = {
            "account": {
                "status": "ACTIVE",
                "account_blocked": False,
                "trading_blocked": False,
                "equity": "100000",
                "cash": "100000",
            },
            "clock": {"is_open": False},
            "open_orders": [],
            "positions": [],
        }
        return pilot, policy, current, previous

    def run_case(self, values):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        names = ["pilot", "policy", "current", "previous"]
        paths = {name: root/f"{name}.json" for name in names}
        for name, value in zip(names, values):
            if value is not None:
                self.write(paths[name], value)

        result = DailyReadOnlyObservation().run(
            pilot_result_path=paths["pilot"],
            current_snapshot_path=paths["current"],
            previous_snapshot_path=paths["previous"],
            observation_policy_path=paths["policy"],
            account_drift_path=root/"drift.json",
            order_watch_path=root/"orders.json",
            position_watch_path=root/"positions.json",
            daily_report_path=root/"daily.json",
            observation_token_path=root/"token.json",
            result_path=root/"result.json",
        )
        return result, root

    def test_wait_before_pilot(self):
        pilot, policy, current, previous = self.data()
        pilot = {
            "status": "PASS",
            "state": "WAIT_FINAL_PRODUCTION_PACKAGE",
            "paper_operations_pilot_ready": False,
            "safe_mode_engaged": False,
        }
        result, _ = self.run_case((pilot, policy, current, previous))
        self.assertEqual(result["state"], "WAIT_PAPER_OPERATIONS_PILOT")

    def test_daily_observation_ready(self):
        result, root = self.run_case(self.data())
        self.assertEqual(result["state"], "DAILY_READ_ONLY_OBSERVATION_READY")
        self.assertTrue(result["daily_read_only_observation_ready"])
        self.assertTrue((root/"token.json").exists())

    def test_equity_drift_blocks(self):
        pilot, policy, current, previous = self.data()
        current = dict(current)
        current["account"] = dict(current["account"])
        current["account"]["equity"] = "105000"
        result, _ = self.run_case((pilot, policy, current, previous))
        self.assertEqual(result["status"], "BLOCKED")

    def test_unexpected_order_blocks(self):
        pilot, policy, current, previous = self.data()
        current = dict(current)
        current["open_orders"] = [{"id": "new-order-1"}]
        result, _ = self.run_case((pilot, policy, current, previous))
        self.assertEqual(result["status"], "BLOCKED")

    def test_unexpected_position_blocks(self):
        pilot, policy, current, previous = self.data()
        current = dict(current)
        current["positions"] = [{"symbol": "AAPL"}]
        result, _ = self.run_case((pilot, policy, current, previous))
        self.assertEqual(result["status"], "BLOCKED")

    def test_submission_policy_blocks(self):
        pilot, policy, current, previous = self.data()
        policy = dict(policy)
        policy["order_submission_enabled"] = True
        result, _ = self.run_case((pilot, policy, current, previous))
        self.assertEqual(result["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
