from __future__ import annotations

import unittest

from autonomous_paper_runtime import (
    AutonomousPaperOrderIdentityReconciler,
    OrderIdentityPolicy,
    OrderIdentityStatus,
    OrderOwnership,
)


def order(**overrides):
    value = {
        "id": "broker-order-1",
        "client_order_id": "BOT-AUTO-PAPER-000001",
        "symbol": "AAPL",
        "side": "buy",
        "qty": "1",
        "type": "limit",
        "time_in_force": "day",
        "status": "new",
        "submitted_at": "2026-08-01T15:00:00Z",
        "filled_qty": "0",
        "limit_price": "50",
    }
    value.update(overrides)
    return value


def ledger(**overrides):
    value = {
        "broker_order_id": "broker-order-1",
        "client_order_id": "BOT-AUTO-PAPER-000001",
    }
    value.update(overrides)
    return value


class OrderIdentityReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.reconciler = AutonomousPaperOrderIdentityReconciler()

    def test_recognized_bot_order(self):
        report = self.reconciler.reconcile(
            open_orders=[order()],
            internal_order_ledger=[ledger()],
        )
        self.assertEqual(report.status, OrderIdentityStatus.MATCHED)
        self.assertFalse(report.safe_mode_engaged)
        self.assertTrue(report.autonomous_order_allowed)
        self.assertEqual(report.bot_order_count, 1)

    def test_external_order_blocks(self):
        report = self.reconciler.reconcile(
            open_orders=[order(client_order_id="manual-order-1")],
            internal_order_ledger=[],
        )
        self.assertEqual(report.status, OrderIdentityStatus.SAFE_MODE)
        self.assertEqual(report.external_order_count, 1)
        self.assertTrue(report.records[0].blocking)

    def test_missing_client_order_id_unknown(self):
        report = self.reconciler.reconcile(
            open_orders=[order(client_order_id="")],
            internal_order_ledger=[],
        )
        self.assertEqual(report.unknown_order_count, 1)
        self.assertEqual(report.records[0].ownership, OrderOwnership.UNKNOWN)

    def test_unrecognized_bot_order_blocks(self):
        report = self.reconciler.reconcile(
            open_orders=[order()],
            internal_order_ledger=[],
        )
        self.assertTrue(report.safe_mode_engaged)
        self.assertEqual(report.records[0].reason,
                         "bot-prefixed order is absent from the internal ledger")

    def test_broker_id_recognition(self):
        report = self.reconciler.reconcile(
            open_orders=[order(client_order_id="BOT-AUTO-PAPER-OTHER")],
            internal_order_ledger=[ledger(client_order_id="different")],
        )
        self.assertTrue(report.records[0].recognized_internal_order)

    def test_unapproved_symbol_blocks(self):
        report = self.reconciler.reconcile(
            open_orders=[order(symbol="TSLA")],
            internal_order_ledger=[ledger()],
        )
        self.assertTrue(report.safe_mode_engaged)

    def test_unsupported_side_blocks(self):
        report = self.reconciler.reconcile(
            open_orders=[order(side="short")],
            internal_order_ledger=[ledger()],
        )
        self.assertTrue(report.safe_mode_engaged)

    def test_no_open_orders(self):
        report = self.reconciler.reconcile(
            open_orders=[],
            internal_order_ledger=[],
        )
        self.assertEqual(report.status, OrderIdentityStatus.NO_OPEN_ORDERS)
        self.assertTrue(report.autonomous_order_allowed)

    def test_external_nonblocking_policy(self):
        policy = OrderIdentityPolicy(block_external_orders=False)
        report = AutonomousPaperOrderIdentityReconciler(policy=policy).reconcile(
            open_orders=[order(client_order_id="manual-1")],
            internal_order_ledger=[],
        )
        self.assertEqual(report.status, OrderIdentityStatus.MATCHED)

    def test_multiple_orders(self):
        report = self.reconciler.reconcile(
            open_orders=[
                order(),
                order(
                    id="broker-order-2",
                    client_order_id="manual-order-2",
                    symbol="SPY",
                ),
            ],
            internal_order_ledger=[ledger()],
        )
        self.assertEqual(report.open_order_count, 2)
        self.assertEqual(report.bot_order_count, 1)
        self.assertEqual(report.external_order_count, 1)
        self.assertEqual(report.blocking_order_count, 1)

    def test_record_fields(self):
        report = self.reconciler.reconcile(
            open_orders=[order()],
            internal_order_ledger=[ledger()],
        )
        record = report.records[0]
        self.assertEqual(record.symbol, "AAPL")
        self.assertEqual(record.side, "BUY")
        self.assertEqual(record.quantity, "1")
        self.assertEqual(record.order_type, "LIMIT")
        self.assertEqual(record.time_in_force, "DAY")
        self.assertEqual(record.status, "NEW")
        self.assertEqual(record.limit_price, "50")

    def test_zero_network_and_orders(self):
        report = self.reconciler.reconcile(
            open_orders=[order()],
            internal_order_ledger=[ledger()],
        )
        self.assertEqual(report.read_requests_executed, 0)
        self.assertEqual(report.write_requests_executed, 0)
        self.assertEqual(report.actual_paper_orders_submitted, 0)
        self.assertEqual(report.live_orders_submitted, 0)

    def test_json_serialization(self):
        report = self.reconciler.reconcile(
            open_orders=[order()],
            internal_order_ledger=[ledger()],
        )
        raw = report.to_json_dict()
        self.assertEqual(raw["status"], "MATCHED")
        self.assertEqual(raw["records"][0]["ownership"], "BOT")

    def test_policy_validation(self):
        with self.assertRaises(ValueError):
            OrderIdentityPolicy(bot_client_order_prefixes=()).validate()


if __name__ == "__main__":
    unittest.main()
