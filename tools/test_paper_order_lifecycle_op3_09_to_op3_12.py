import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autonomous_paper_runtime.paper_order_lifecycle_reconciliation import (
    LIVE_BASE_URL,
    PaperOrderLifecycleReconciliation,
)


class Tests(unittest.TestCase):
    def write(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def data(self):
        execution = {
            "submission_succeeded": True,
            "actual_paper_orders_submitted": 1,
            "safe_mode_engaged": False,
            "broker_order_id": "order-1",
            "client_order_id": "client-1",
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 1,
        }
        receipt = {
            "broker_order_id": "order-1",
            "client_order_id": "client-1",
        }
        policy = {
            "lifecycle_id": "lifecycle-1",
            "paper_only": True,
            "read_only": True,
            "order_write_enabled": False,
            "cancel_enabled": False,
            "replace_enabled": False,
            "timeout_seconds": 10,
            "expected_base_url": "https://paper-api.alpaca.markets",
        }
        order = {
            "id": "order-1",
            "client_order_id": "client-1",
            "symbol": "AAPL",
            "side": "buy",
            "qty": "1",
            "status": "filled",
            "filled_qty": "1",
            "filled_avg_price": "50.25",
        }
        positions = {
            "positions": [{"symbol": "AAPL", "qty": "1"}]
        }
        account = {
            "status": "ACTIVE",
            "account_blocked": False,
            "trading_blocked": False,
        }
        return execution, receipt, policy, order, positions, account

    def run_case(
        self,
        values,
        *,
        enable_network=False,
        base_url="https://paper-api.alpaca.markets",
        transport=None,
    ):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        names = ["execution", "receipt", "policy", "order", "positions", "account"]
        paths = {name: root/f"{name}.json" for name in names}
        for name, value in zip(names, values):
            if value is not None:
                self.write(paths[name], value)

        result = PaperOrderLifecycleReconciliation().run(
            execution_result_path=paths["execution"],
            submission_receipt_path=paths["receipt"],
            lifecycle_policy_path=paths["policy"],
            local_order_snapshot_path=paths["order"],
            local_positions_snapshot_path=paths["positions"],
            local_account_snapshot_path=paths["account"],
            order_status_path=root/"status.json",
            fill_report_path=root/"fill.json",
            reconciliation_report_path=root/"recon.json",
            recovery_token_path=root/"recovery.json",
            audit_ledger_path=root/"ledger.jsonl",
            result_path=root/"result.json",
            enable_network=enable_network,
            base_url=base_url,
            transport=transport,
        )
        return result, root

    def test_filled_order_reconciles(self):
        result, root = self.run_case(self.data())
        self.assertEqual(result["state"], "PAPER_ORDER_LIFECYCLE_COMPLETE")
        self.assertTrue(result["position_reconciled"])
        self.assertEqual(result["write_requests_executed"], 0)
        self.assertTrue((root/"ledger.jsonl").exists())

    def test_open_order_requires_recovery(self):
        values = list(self.data())
        values[3] = dict(values[3])
        values[3]["status"] = "accepted"
        values[3]["filled_qty"] = "0"
        values[4] = {"positions": []}
        result, _ = self.run_case(tuple(values))
        self.assertEqual(result["state"], "PAPER_ORDER_LIFECYCLE_MONITORING")
        self.assertTrue(result["recovery_required"])

    def test_position_mismatch_blocks(self):
        values = list(self.data())
        values[4] = {"positions": [{"symbol": "AAPL", "qty": "2"}]}
        result, _ = self.run_case(tuple(values))
        self.assertEqual(result["status"], "BLOCKED")

    def test_live_endpoint_blocks(self):
        result, _ = self.run_case(self.data(), base_url=LIVE_BASE_URL)
        self.assertEqual(result["status"], "BLOCKED")

    def test_prior_submission_required(self):
        values = list(self.data())
        values[0] = dict(values[0])
        values[0]["submission_succeeded"] = False
        values[0]["actual_paper_orders_submitted"] = 0
        result, _ = self.run_case(tuple(values))
        self.assertEqual(result["status"], "BLOCKED")

    def test_mock_network_read_only(self):
        order = self.data()[3]
        positions = self.data()[4]["positions"]
        account = self.data()[5]

        def transport(**kwargs):
            url = kwargs["url"]
            if "/v2/orders/" in url:
                return 200, order
            if url.endswith("/v2/positions"):
                return 200, positions
            return 200, account

        values = self.data()
        with patch.dict(
            os.environ,
            {
                "APCA_API_KEY_ID": "paper-key",
                "APCA_API_SECRET_KEY": "paper-secret",
            },
            clear=False,
        ):
            result, _ = self.run_case(
                values,
                enable_network=True,
                transport=transport,
            )
        self.assertEqual(result["network_requests_executed"], 3)
        self.assertEqual(result["write_requests_executed"], 0)
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
