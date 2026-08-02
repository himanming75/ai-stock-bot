from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path

from autonomous_paper_runtime.submitted_order_acceptance_verification import (
    SubmittedOrderAcceptanceVerification,
)


class Tests(unittest.TestCase):
    def launch(self):
        return {
            "status": "PASS",
            "state": "ORDER_SUBMISSION_PREPARED",
            "submission_prepared": True,
            "client_order_id": "v13907-test",
            "safe_mode_engaged": False,
        }

    def prep(self):
        return {
            "client_order_id": "v13907-test",
            "submission_prepared": True,
            "actual_submission_allowed": False,
            "broker_network_allowed": False,
        }

    def preview(self):
        return {
            "client_order_id": "v13907-test",
            "symbol": "SPY",
            "side": "BUY",
            "quantity": 1,
            "order_type": "MARKET",
            "time_in_force": "DAY",
        }

    def snapshot(self, status="ACCEPTED"):
        return {
            "client_order_id": "v13907-test",
            "broker_order_id": "broker-001",
            "status": status,
            "symbol": "SPY",
            "side": "BUY",
            "quantity": 1,
            "order_type": "MARKET",
            "time_in_force": "DAY",
        }

    def run_case(self, launch, prep=None, preview=None, snapshot=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        launch_path = root / "launch.json"
        prep_path = root / "prep.json"
        preview_path = root / "preview.json"
        snapshot_path = root / "snapshot.json"
        token_path = root / "token.json"
        result_path = root / "result.json"
        launch_path.write_text(json.dumps(launch), encoding="utf-8")
        if prep is not None:
            prep_path.write_text(json.dumps(prep), encoding="utf-8")
        if preview is not None:
            preview_path.write_text(json.dumps(preview), encoding="utf-8")
        if snapshot is not None:
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
        report = SubmittedOrderAcceptanceVerification().run(
            launch_result_path=launch_path,
            preparation_token_path=prep_path,
            preview_path=preview_path,
            submission_snapshot_path=snapshot_path,
            acceptance_token_path=token_path,
            result_path=result_path,
        )
        return report, token_path

    def test_waits_before_submission_prepared(self):
        report, token = self.run_case({
            "status": "PASS",
            "state": "WAIT_ELIGIBILITY",
            "submission_prepared": False,
            "client_order_id": "",
            "safe_mode_engaged": False,
        })
        self.assertEqual(report.state, "WAIT_SUBMISSION_RESULT")
        self.assertFalse(token.exists())

    def test_accepted_snapshot_creates_token(self):
        report, token = self.run_case(
            self.launch(), self.prep(), self.preview(), self.snapshot("ACCEPTED")
        )
        self.assertEqual(report.state, "ORDER_ACCEPTED")
        self.assertTrue(report.lifecycle_monitor_ready)
        self.assertTrue(token.exists())

    def test_pending_new_is_accepted_path(self):
        report, _ = self.run_case(
            self.launch(), self.prep(), self.preview(), self.snapshot("PENDING_NEW")
        )
        self.assertEqual(report.state, "ORDER_ACCEPTED")

    def test_rejected_snapshot_is_terminal_rejection(self):
        report, token = self.run_case(
            self.launch(), self.prep(), self.preview(), self.snapshot("REJECTED")
        )
        self.assertEqual(report.state, "ORDER_REJECTED")
        self.assertTrue(report.order_rejected)
        self.assertFalse(token.exists())

    def test_missing_snapshot_blocks_after_preparation(self):
        report, _ = self.run_case(self.launch(), self.prep(), self.preview())
        self.assertEqual(report.status, "BLOCKED")

    def test_client_order_id_mismatch_blocks(self):
        snapshot = self.snapshot()
        snapshot["client_order_id"] = "different"
        report, _ = self.run_case(
            self.launch(), self.prep(), self.preview(), snapshot
        )
        self.assertEqual(report.status, "BLOCKED")

    def test_quantity_mismatch_blocks(self):
        snapshot = self.snapshot()
        snapshot["quantity"] = 2
        report, _ = self.run_case(
            self.launch(), self.prep(), self.preview(), snapshot
        )
        self.assertEqual(report.status, "BLOCKED")

    def test_unsupported_status_blocks(self):
        report, _ = self.run_case(
            self.launch(), self.prep(), self.preview(), self.snapshot("FILLED")
        )
        self.assertEqual(report.status, "BLOCKED")


if __name__ == "__main__":
    unittest.main()
