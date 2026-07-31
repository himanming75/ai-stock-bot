from __future__ import annotations

import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from broker.contracts_v77_1 import (
    BrokerOrderRequest,
    BrokerOrderStatus,
    OrderSide,
    OrderType,
    TimeInForce,
)
from broker.order_lifecycle_simulator_v77_3 import OrderLifecycleSimulator
from broker.sandbox_adapter_v77_2 import SandboxBrokerError
from tools.order_lifecycle_simulator_v77_3 import verify, write_outputs
from tools.verify_order_lifecycle_simulator_v77_3 import verify_output


class LifecycleTests(unittest.TestCase):
    def request(self, side=OrderSide.BUY, quantity="10", client="order-1"):
        return BrokerOrderRequest(
            client_order_id=client,
            symbol="AAPL",
            side=side,
            quantity=Decimal(quantity),
            order_type=OrderType.LIMIT,
            time_in_force=TimeInForce.DAY,
            limit_price=Decimal("100"),
        )

    def test_partial_then_full_fill(self):
        sim = OrderLifecycleSimulator()
        order = sim.submit_order(self.request())
        partial = sim.apply_fill(order.broker_order_id, quantity=Decimal("4"), price=Decimal("100"))
        self.assertEqual(partial.status, BrokerOrderStatus.PARTIALLY_FILLED)
        full = sim.apply_fill(order.broker_order_id, quantity=Decimal("6"), price=Decimal("110"))
        self.assertEqual(full.status, BrokerOrderStatus.FILLED)
        self.assertEqual(full.average_fill_price, Decimal("106"))

    def test_cash_and_position_update(self):
        sim = OrderLifecycleSimulator()
        order = sim.submit_order(self.request())
        sim.apply_fill(order.broker_order_id, quantity=Decimal("10"), price=Decimal("100"))
        snapshot = sim.get_account_snapshot()
        self.assertEqual(snapshot.cash, Decimal("99000"))
        self.assertEqual(snapshot.positions[0].quantity, Decimal("10"))
        self.assertEqual(snapshot.equity, Decimal("100000"))

    def test_sell_reduces_position(self):
        sim = OrderLifecycleSimulator()
        buy = sim.submit_order(self.request())
        sim.apply_fill(buy.broker_order_id, quantity=Decimal("10"), price=Decimal("100"))
        sell = sim.submit_order(self.request(OrderSide.SELL, "3", "sell-1"))
        sim.apply_fill(sell.broker_order_id, quantity=Decimal("3"), price=Decimal("120"))
        snapshot = sim.get_account_snapshot()
        self.assertEqual(snapshot.cash, Decimal("99360"))
        self.assertEqual(snapshot.positions[0].quantity, Decimal("7"))

    def test_overfill_rejected(self):
        sim = OrderLifecycleSimulator()
        order = sim.submit_order(self.request(quantity="2"))
        with self.assertRaises(SandboxBrokerError):
            sim.apply_fill(order.broker_order_id, quantity=Decimal("3"), price=Decimal("100"))

    def test_insufficient_cash_rejected(self):
        sim = OrderLifecycleSimulator(starting_cash=Decimal("50"))
        order = sim.submit_order(self.request(quantity="1"))
        with self.assertRaises(SandboxBrokerError):
            sim.apply_fill(order.broker_order_id, quantity=Decimal("1"), price=Decimal("100"))

    def test_short_sell_rejected(self):
        sim = OrderLifecycleSimulator()
        sell = sim.submit_order(self.request(OrderSide.SELL, "1", "sell-1"))
        with self.assertRaises(SandboxBrokerError):
            sim.apply_fill(sell.broker_order_id, quantity=Decimal("1"), price=Decimal("100"))

    def test_filled_order_cannot_be_canceled(self):
        sim = OrderLifecycleSimulator()
        order = sim.submit_order(self.request(quantity="1"))
        sim.apply_fill(order.broker_order_id, quantity=Decimal("1"), price=Decimal("100"))
        with self.assertRaises(SandboxBrokerError):
            sim.cancel_order(order.broker_order_id)

    def test_verification_outputs(self):
        config = {
            "expected_framework_commit_sha": "a"*7,
            "expected_v77_2_adapter_sha256": "b"*64,
            "expected_v77_2_verification_sha256": "c"*64,
            "starting_cash": "100000.00",
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root/"release/v77_2/output"
            out.mkdir(parents=True)
            (out/"sandbox_broker_adapter_verification_v77_2.json").write_text(
                json.dumps({
                    "status": "PASS",
                    "sandbox_broker_adapter_sha256": "b"*64,
                    "verification_sha256": "c"*64,
                    "next_phase": "V77_3_ORDER_LIFECYCLE_SIMULATOR",
                }),
                encoding="utf-8",
            )
            git = {
                "head_sha": "d"*40,
                "origin_main_sha": "d"*40,
                "branch": "main",
                "tracked_status_short": [],
            }
            with (
                patch("tools.order_lifecycle_simulator_v77_3.git_state", return_value=git),
                patch("tools.order_lifecycle_simulator_v77_3.git_is_ancestor", return_value=True),
            ):
                result = verify(root, config)
            self.assertEqual(result["status"], "PASS")
            output_dir = root/"release/v77_3/output"
            write_outputs(result, output_dir)
            self.assertTrue(verify_output(output_dir)["verified"])


if __name__ == "__main__":
    unittest.main()
