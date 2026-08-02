import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autonomous_paper_runtime.single_controlled_paper_order_execution import (
    LIVE_BASE_URL,
    SUBMISSION_APPROVAL_PHRASE,
    SingleControlledPaperOrderExecution,
)


class Tests(unittest.TestCase):
    def write(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def data(self):
        preparation = {
            "controlled_paper_order_preparation_ready": True,
            "manual_approval_ready": True,
            "safe_mode_engaged": False,
        }
        prepared = {
            "candidate_id": "paper-candidate-1234567890abcdef",
            "symbol": "AAPL",
            "side": "buy",
            "order_type": "market",
            "time_in_force": "day",
            "quantity": 1,
            "reference_price": 50,
            "estimated_notional": 50,
            "endpoint": "https://paper-api.alpaca.markets",
            "paper_only": True,
            "submission_attempted": False,
        }
        policy = {
            "execution_id": "execution-001",
            "paper_only": True,
            "maximum_orders_per_run": 1,
            "maximum_order_notional": 100,
            "maximum_order_quantity": 5,
            "market_order_only": True,
            "day_time_in_force_only": True,
            "live_trading_enabled": False,
            "expected_base_url": (
                "https://paper-api.alpaca.markets"
            ),
            "timeout_seconds": 10,
        }
        return preparation, prepared, policy

    def run_case(
        self,
        values,
        *,
        enable_network=False,
        enable_submission=False,
        approval_phrase="",
        base_url="https://paper-api.alpaca.markets",
        transport=None,
    ):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        names = ["preparation", "prepared", "policy"]
        paths = {name: root/f"{name}.json" for name in names}
        for name, value in zip(names, values):
            if value is not None:
                self.write(paths[name], value)

        result = SingleControlledPaperOrderExecution().run(
            preparation_result_path=paths["preparation"],
            prepared_order_path=paths["prepared"],
            execution_policy_path=paths["policy"],
            submission_receipt_path=root/"receipt.json",
            execution_ledger_path=root/"ledger.jsonl",
            execution_token_path=root/"token.json",
            result_path=root/"result.json",
            enable_network=enable_network,
            enable_submission=enable_submission,
            approval_phrase=approval_phrase,
            base_url=base_url,
            transport=transport,
        )
        return result, root

    def test_default_is_armed_preview_only(self):
        result, _ = self.run_case(self.data())
        self.assertEqual(
            result["state"],
            "SINGLE_PAPER_ORDER_EXECUTION_ARMED",
        )
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["actual_paper_orders_submitted"], 0)

    def test_live_endpoint_blocks(self):
        result, _ = self.run_case(
            self.data(),
            base_url=LIVE_BASE_URL,
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_missing_submission_phrase_does_not_submit(self):
        with patch.dict(
            os.environ,
            {
                "APCA_API_KEY_ID": "paper-key",
                "APCA_API_SECRET_KEY": "paper-secret",
            },
            clear=False,
        ):
            result, _ = self.run_case(
                self.data(),
                enable_network=True,
                enable_submission=True,
            )
        self.assertEqual(result["state"], "SINGLE_PAPER_ORDER_EXECUTION_ARMED")
        self.assertFalse(result["submission_gate_ready"])

    def test_mock_submission_succeeds_once(self):
        def transport(**kwargs):
            return 200, {
                "id": "paper-order-001",
                "status": "accepted",
                "client_order_id": kwargs["body"]["client_order_id"],
            }

        with patch.dict(
            os.environ,
            {
                "APCA_API_KEY_ID": "paper-key",
                "APCA_API_SECRET_KEY": "paper-secret",
            },
            clear=False,
        ):
            result, root = self.run_case(
                self.data(),
                enable_network=True,
                enable_submission=True,
                approval_phrase=SUBMISSION_APPROVAL_PHRASE,
                transport=transport,
            )
        self.assertEqual(
            result["state"],
            "SINGLE_CONTROLLED_PAPER_ORDER_SUBMITTED",
        )
        self.assertEqual(result["actual_paper_orders_submitted"], 1)
        self.assertEqual(result["live_orders_submitted"], 0)
        self.assertTrue((root/"receipt.json").exists())
        self.assertTrue((root/"ledger.jsonl").exists())

    def test_notional_limit_blocks(self):
        preparation, prepared, policy = self.data()
        prepared = dict(prepared)
        prepared["estimated_notional"] = 150
        result, _ = self.run_case(
            (preparation, prepared, policy)
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_preparation_approval_required(self):
        preparation, prepared, policy = self.data()
        preparation = dict(preparation)
        preparation["manual_approval_ready"] = False
        result, _ = self.run_case(
            (preparation, prepared, policy)
        )
        self.assertEqual(result["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
