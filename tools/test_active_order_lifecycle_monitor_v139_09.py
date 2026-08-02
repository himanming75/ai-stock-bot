from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path

from autonomous_paper_runtime.active_order_lifecycle_monitor import ActiveOrderLifecycleMonitor


class Tests(unittest.TestCase):
    def acceptance(self):
        return {
            "status": "PASS",
            "state": "ORDER_ACCEPTED",
            "client_order_id": "client-001",
            "broker_order_id": "broker-001",
            "lifecycle_monitor_ready": True,
            "safe_mode_engaged": False,
        }

    def token(self):
        return {
            "client_order_id": "client-001",
            "broker_order_id": "broker-001",
            "lifecycle_monitor_ready": True,
        }

    def snapshot(self, status="ACCEPTED", filled=0, quantity=10):
        return {
            "client_order_id": "client-001",
            "broker_order_id": "broker-001",
            "status": status,
            "quantity": quantity,
            "filled_quantity": filled,
            "average_fill_price": 100 if filled else 0,
        }

    def run_case(self, acceptance, token=None, snapshot=None, previous=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        acceptance_path = root / "acceptance.json"
        token_path = root / "token.json"
        snapshot_path = root / "snapshot.json"
        previous_path = root / "previous.json"
        monitor_path = root / "monitor.json"
        result_path = root / "result.json"
        acceptance_path.write_text(json.dumps(acceptance), encoding="utf-8")
        if token is not None:
            token_path.write_text(json.dumps(token), encoding="utf-8")
        if snapshot is not None:
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
        if previous is not None:
            previous_path.write_text(json.dumps(previous), encoding="utf-8")
        report = ActiveOrderLifecycleMonitor().run(
            acceptance_result_path=acceptance_path,
            acceptance_token_path=token_path,
            lifecycle_snapshot_path=snapshot_path,
            previous_lifecycle_snapshot_path=previous_path,
            monitor_state_path=monitor_path,
            result_path=result_path,
        )
        return report

    def test_waits_before_acceptance(self):
        report = self.run_case({
            "status": "PASS",
            "state": "WAIT_SUBMISSION_RESULT",
            "client_order_id": "",
            "broker_order_id": "",
            "lifecycle_monitor_ready": False,
            "safe_mode_engaged": False,
        })
        self.assertEqual(report.state, "WAIT_ACCEPTANCE")

    def test_active_order_monitoring(self):
        report = self.run_case(self.acceptance(), self.token(), self.snapshot())
        self.assertEqual(report.state, "ACTIVE_ORDER_MONITORING")
        self.assertTrue(report.active_order_present)

    def test_partial_fill(self):
        report = self.run_case(
            self.acceptance(), self.token(), self.snapshot("PARTIALLY_FILLED", 4, 10)
        )
        self.assertEqual(report.state, "PARTIALLY_FILLED")
        self.assertEqual(report.remaining_quantity, 6)

    def test_filled_is_terminal(self):
        report = self.run_case(
            self.acceptance(), self.token(), self.snapshot("FILLED", 10, 10)
        )
        self.assertEqual(report.state, "TERMINAL_OBSERVED")
        self.assertTrue(report.terminal_commit_ready)

    def test_canceled_is_terminal(self):
        report = self.run_case(
            self.acceptance(), self.token(), self.snapshot("CANCELED", 3, 10)
        )
        self.assertEqual(report.state, "TERMINAL_OBSERVED")

    def test_fill_quantity_regression_blocks(self):
        previous = self.snapshot("PARTIALLY_FILLED", 5, 10)
        report = self.run_case(
            self.acceptance(), self.token(),
            self.snapshot("PARTIALLY_FILLED", 4, 10), previous
        )
        self.assertEqual(report.status, "BLOCKED")

    def test_status_regression_blocks(self):
        previous = self.snapshot("PARTIALLY_FILLED", 4, 10)
        report = self.run_case(
            self.acceptance(), self.token(),
            self.snapshot("ACCEPTED", 4, 10), previous
        )
        self.assertEqual(report.status, "BLOCKED")

    def test_filled_quantity_over_order_quantity_blocks(self):
        report = self.run_case(
            self.acceptance(), self.token(), self.snapshot("FILLED", 11, 10)
        )
        self.assertEqual(report.status, "BLOCKED")

    def test_missing_snapshot_after_acceptance_blocks(self):
        report = self.run_case(self.acceptance(), self.token())
        self.assertEqual(report.status, "BLOCKED")


if __name__ == "__main__":
    unittest.main()
