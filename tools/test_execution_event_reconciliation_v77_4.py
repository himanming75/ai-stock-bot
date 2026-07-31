from __future__ import annotations

import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from broker.contracts_v77_1 import (
    BrokerOrderRequest,
    OrderSide,
    OrderType,
    TimeInForce,
)
from broker.execution_event_reconciliation_v77_4 import ExecutionEventReconciler
from broker.order_lifecycle_simulator_v77_3 import OrderLifecycleSimulator
from tools.execution_event_reconciliation_v77_4 import verify, write_outputs
from tools.verify_execution_event_reconciliation_v77_4 import verify_output


class ReconciliationTests(unittest.TestCase):
    def scenario(self):
        sim = OrderLifecycleSimulator()
        buy = sim.submit_order(BrokerOrderRequest(
            client_order_id="buy-1",
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("10"),
            order_type=OrderType.LIMIT,
            time_in_force=TimeInForce.DAY,
            limit_price=Decimal("100"),
        ))
        sim.apply_fill(buy.broker_order_id, quantity=Decimal("4"), price=Decimal("100"))
        sim.apply_fill(buy.broker_order_id, quantity=Decimal("6"), price=Decimal("110"))
        sell = sim.submit_order(BrokerOrderRequest(
            client_order_id="sell-1",
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=Decimal("3"),
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
        ))
        sim.apply_fill(sell.broker_order_id, quantity=Decimal("3"), price=Decimal("120"))
        return sim

    def test_clean_reconciliation(self):
        report = ExecutionEventReconciler().reconcile(self.scenario())
        self.assertTrue(report.passed)
        self.assertEqual(report.issue_count, 0)
        self.assertEqual(report.expected_cash, report.actual_cash)

    def test_detects_cash_tamper(self):
        sim = self.scenario()
        sim._cash += Decimal("1")
        report = ExecutionEventReconciler().reconcile(sim)
        self.assertFalse(report.passed)
        self.assertIn("CASH_BALANCE_MISMATCH", {i.code for i in report.issues})

    def test_detects_order_fill_tamper(self):
        sim = self.scenario()
        order_id = sim.list_orders()[0].broker_order_id
        order = sim._orders[order_id]
        sim._orders[order_id] = type(order)(
            broker_order_id=order.broker_order_id,
            request=order.request,
            status=order.status,
            filled_quantity=Decimal("9"),
            average_fill_price=order.average_fill_price,
            submitted_at_utc=order.submitted_at_utc,
            updated_at_utc=order.updated_at_utc,
            rejection_reason=order.rejection_reason,
        )
        report = ExecutionEventReconciler().reconcile(sim)
        self.assertIn("ORDER_FILL_QUANTITY_MISMATCH", {i.code for i in report.issues})

    def test_detects_position_tamper(self):
        sim = self.scenario()
        sim._positions["AAPL"].quantity = Decimal("8")
        report = ExecutionEventReconciler().reconcile(sim)
        self.assertIn("POSITION_QUANTITY_MISMATCH", {i.code for i in report.issues})

    def test_verification_outputs(self):
        config = {
            "expected_framework_commit_sha": "a"*7,
            "expected_v77_3_lifecycle_sha256": "b"*64,
            "expected_v77_3_verification_sha256": "c"*64,
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root/"release/v77_3/output"
            out.mkdir(parents=True)
            (out/"order_lifecycle_simulator_verification_v77_3.json").write_text(
                json.dumps({
                    "status": "PASS",
                    "order_lifecycle_simulator_sha256": "b"*64,
                    "verification_sha256": "c"*64,
                    "next_phase": "V77_4_EXECUTION_EVENT_RECONCILIATION",
                }),
                encoding="utf-8",
            )
            git = {
                "head_sha": "d"*40,
                "origin_main_sha": "d"*40,
                "branch": "main",
            }
            with (
                patch("tools.execution_event_reconciliation_v77_4.git_state",
                      return_value=git),
                patch("tools.execution_event_reconciliation_v77_4.git_is_ancestor",
                      return_value=True),
            ):
                result = verify(root, config)
            self.assertEqual(result["status"], "PASS")
            output_dir = root/"release/v77_4/output"
            write_outputs(result, output_dir)
            self.assertTrue(verify_output(output_dir)["verified"])


if __name__ == "__main__":
    unittest.main()
