import json
import tempfile
import unittest
from pathlib import Path

from paper_pilot.multi_day_validation import (
    MultiDayPaperValidationFoundation,
)


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
            "minimum_validation_days": 3,
            "minimum_consecutive_healthy_days": 2,
            "maximum_unhealthy_days": 1,
            "maximum_validation_records": 30,
        }
        foundation = {
            "pilot_started": True,
            "pilot_id": "pilot-1",
            "session_id": "session-1",
        }
        session = {"health_status": "HEALTHY"}
        performance = {
            "state": "PAPER_PERFORMANCE_SAMPLE_COLLECTED",
            "latest_equity": 100100,
            "cumulative_return_pct": 0.1,
        }
        risk = {
            "state": "PAPER_RISK_HEALTHY",
            "emergency_stop_required": False,
            "max_drawdown_pct": 0.1,
            "daily_loss_pct": 0,
            "gross_exposure_pct": 10,
        }
        automation = {
            "state": "PILOT_AUTOMATION_READY",
            "recovery_gate_clear": True,
            "snapshot_ready": True,
        }
        return policy, foundation, session, performance, risk, automation

    def run_case(self, values, *, record=False, validation_date=None):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        names = [
            "policy", "foundation", "session",
            "performance", "risk", "automation",
        ]
        paths = {name: root/f"{name}.json" for name in names}
        for name, value in zip(names, values):
            self.write(paths[name], value)

        result = MultiDayPaperValidationFoundation().run(
            policy_path=paths["policy"],
            foundation_result_path=paths["foundation"],
            session_result_path=paths["session"],
            performance_result_path=paths["performance"],
            risk_result_path=paths["risk"],
            automation_result_path=paths["automation"],
            validation_ledger_path=root/"ledger.jsonl",
            daily_record_path=root/"day.json",
            validation_summary_path=root/"summary.json",
            validation_gate_path=root/"gate.json",
            dashboard_state_path=root/"dashboard.json",
            result_path=root/"result.json",
            record_validation_day=record,
            validation_date=validation_date,
        )
        return result, root

    def test_wait_before_pilot_start(self):
        values = list(self.data())
        values[1] = {"pilot_started": False}
        result, _ = self.run_case(tuple(values))
        self.assertEqual(result["state"], "WAIT_PILOT_START")

    def test_records_healthy_day(self):
        result, root = self.run_case(
            self.data(),
            record=True,
            validation_date="2026-08-03",
        )
        self.assertTrue(result["record_written"])
        self.assertTrue(result["day_healthy"])
        self.assertTrue((root/"ledger.jsonl").exists())

    def test_duplicate_date_blocks(self):
        values = self.data()
        result, root = self.run_case(
            values,
            record=True,
            validation_date="2026-08-03",
        )
        self.assertTrue(result["record_written"])
        second = MultiDayPaperValidationFoundation().run(
            policy_path=root/"policy.json",
            foundation_result_path=root/"foundation.json",
            session_result_path=root/"session.json",
            performance_result_path=root/"performance.json",
            risk_result_path=root/"risk.json",
            automation_result_path=root/"automation.json",
            validation_ledger_path=root/"ledger.jsonl",
            daily_record_path=root/"day2.json",
            validation_summary_path=root/"summary2.json",
            validation_gate_path=root/"gate2.json",
            dashboard_state_path=root/"dashboard2.json",
            result_path=root/"result2.json",
            record_validation_day=True,
            validation_date="2026-08-03",
        )
        self.assertEqual(second["status"], "BLOCKED")
        self.assertTrue(second["duplicate_validation_date"])

    def test_unhealthy_day_recorded(self):
        values = list(self.data())
        values[4] = {
            "state": "EMERGENCY_STOP_REQUIRED",
            "emergency_stop_required": True,
        }
        result, _ = self.run_case(
            tuple(values),
            record=True,
            validation_date="2026-08-03",
        )
        self.assertTrue(result["record_written"])
        self.assertFalse(result["day_healthy"])

    def test_validation_completion(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        values = self.data()
        names = [
            "policy", "foundation", "session",
            "performance", "risk", "automation",
        ]
        for name, value in zip(names, values):
            self.write(root/f"{name}.json", value)

        for day in ["2026-08-01", "2026-08-02", "2026-08-03"]:
            result = MultiDayPaperValidationFoundation().run(
                policy_path=root/"policy.json",
                foundation_result_path=root/"foundation.json",
                session_result_path=root/"session.json",
                performance_result_path=root/"performance.json",
                risk_result_path=root/"risk.json",
                automation_result_path=root/"automation.json",
                validation_ledger_path=root/"ledger.jsonl",
                daily_record_path=root/"day.json",
                validation_summary_path=root/"summary.json",
                validation_gate_path=root/"gate.json",
                dashboard_state_path=root/"dashboard.json",
                result_path=root/"result.json",
                record_validation_day=True,
                validation_date=day,
            )
        self.assertTrue(result["validation_complete"])
        self.assertEqual(result["state"], "MULTI_DAY_VALIDATION_COMPLETE")

    def test_read_only_contract(self):
        result, _ = self.run_case(self.data())
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["write_requests_executed"], 0)
        self.assertFalse(result["broker_write_enabled"])


if __name__ == "__main__":
    unittest.main()
