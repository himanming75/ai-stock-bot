from __future__ import annotations

import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from broker.contracts_v77_1 import (
    BrokerContract,
    BrokerOrderRequest,
    BrokerOrderStatus,
    OrderSide,
    OrderType,
    TimeInForce,
)
from broker.sandbox_adapter_v77_2 import SandboxBrokerAdapter, SandboxBrokerError
from tools.sandbox_broker_adapter_v77_2 import (
    validate_config,
    verify_adapter,
    write_outputs,
)
from tools.verify_sandbox_broker_adapter_v77_2 import verify_output


class SandboxAdapterTests(unittest.TestCase):
    def request(self, client_order_id: str = "test-order-1") -> BrokerOrderRequest:
        return BrokerOrderRequest(
            client_order_id=client_order_id,
            symbol="aapl",
            side=OrderSide.BUY,
            quantity=Decimal("2"),
            order_type=OrderType.LIMIT,
            time_in_force=TimeInForce.DAY,
            limit_price=Decimal("190"),
        )

    def test_runtime_contract(self) -> None:
        adapter = SandboxBrokerAdapter()
        self.assertIsInstance(adapter, BrokerContract)

    def test_health_is_offline(self) -> None:
        health = SandboxBrokerAdapter().health()
        self.assertFalse(health.connected)
        self.assertFalse(health.authenticated)
        self.assertFalse(health.network_used)

    def test_submit_is_simulated_only(self) -> None:
        adapter = SandboxBrokerAdapter()
        order = adapter.submit_order(self.request())
        self.assertEqual(order.status, BrokerOrderStatus.ACCEPTED)
        self.assertEqual(order.request.symbol, "AAPL")
        self.assertEqual(adapter.actual_orders_submitted, 0)
        self.assertEqual(adapter.simulated_order_count, 1)

    def test_duplicate_client_order_id_rejected(self) -> None:
        adapter = SandboxBrokerAdapter()
        adapter.submit_order(self.request())
        with self.assertRaises(SandboxBrokerError):
            adapter.submit_order(self.request())

    def test_cancel(self) -> None:
        adapter = SandboxBrokerAdapter()
        accepted = adapter.submit_order(self.request())
        canceled = adapter.cancel_order(accepted.broker_order_id)
        self.assertEqual(canceled.status, BrokerOrderStatus.CANCELED)
        self.assertEqual(adapter.get_account_snapshot().open_orders, ())

    def test_unknown_cancel_rejected(self) -> None:
        with self.assertRaises(SandboxBrokerError):
            SandboxBrokerAdapter().cancel_order("missing")

    def test_event_ledger(self) -> None:
        adapter = SandboxBrokerAdapter()
        accepted = adapter.submit_order(self.request())
        adapter.cancel_order(accepted.broker_order_id)
        event_types = [event.event_type for event in adapter.event_ledger()]
        self.assertIn("adapter_initialized", event_types)
        self.assertIn("simulated_order_accepted", event_types)
        self.assertIn("simulated_order_canceled", event_types)

    def test_verification_and_independent_verifier(self) -> None:
        config = {
            "adapter_scope": "SANDBOX_BROKER_ADAPTER",
            "expected_framework_commit_sha": "a" * 7,
            "expected_v77_1_broker_contract_sha256": "b" * 64,
            "expected_v77_1_verification_sha256": "c" * 64,
            "required_adapter_name": "memory_sandbox_broker_v77_2",
            "required_environment": "offline",
            "starting_cash": "100000.00",
            "network_allowed": False,
            "broker_connection_allowed": False,
            "actual_order_submission_allowed": False,
            "live_trading_allowed": False,
            "live_approval_allowed": False,
            "fills_allowed": False,
            "require_duplicate_client_order_id_rejection": True,
            "require_cancel_support": True,
            "require_zero_actual_orders": True,
            "require_event_ledger": True,
        }
        validate_config(config)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_dir = root / "release/v77_1/output"
            source_dir.mkdir(parents=True)
            source = {
                "status": "PASS",
                "broker_contract_sha256": "b" * 64,
                "verification_sha256": "c" * 64,
                "next_phase": "V77_2_SANDBOX_BROKER_ADAPTER",
            }
            (source_dir / "broker_interface_contract_verification_v77_1.json").write_text(
                json.dumps(source), encoding="utf-8"
            )
            git = {
                "head_sha": "a" * 40,
                "head_short_sha": "a" * 7,
                "origin_main_sha": "a" * 40,
                "branch": "main",
                "tracked_status_short": [],
            }
            with patch("tools.sandbox_broker_adapter_v77_2.git_state", return_value=git):
                result = verify_adapter(root, config)
            self.assertEqual(result["status"], "PASS")
            output = root / "release/v77_2/output"
            write_outputs(result, output)
            self.assertTrue(verify_output(output)["verified"])


if __name__ == "__main__":
    unittest.main()
