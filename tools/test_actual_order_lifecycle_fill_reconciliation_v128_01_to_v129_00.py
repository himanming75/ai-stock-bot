from __future__ import annotations

from decimal import Decimal
import unittest

from autonomous_paper_runtime.fill_reconciliation import (
    ActualOrderLifecycleFillReconciler,
    FillReconciliationState,
)


def order(**overrides):
    value = {
        "id": "broker-1",
        "client_order_id": "single-legacy",
        "symbol": "AAPL",
        "side": "buy",
        "quantity": "1",
        "filled_quantity": "0",
        "average_fill_price": "0",
        "status": "accepted",
    }
    value.update(overrides)
    return value


def position(**overrides):
    value = {
        "symbol": "AAPL",
        "quantity": "1",
        "average_entry_price": "50",
    }
    value.update(overrides)
    return value


class FillReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.reconciler = ActualOrderLifecycleFillReconciler()

    def test_active_waits(self):
        report = self.reconciler.reconcile(
            order=order(),
            positions=[],
            account={"cash": "100000", "equity": "100000"},
        )
        self.assertEqual(report.state, FillReconciliationState.WAITING_ACTIVE_ORDER)
        self.assertFalse(report.new_order_allowed)

    def test_partial_waits(self):
        report = self.reconciler.reconcile(
            order=order(
                status="partially_filled",
                filled_quantity="0.4",
                average_fill_price="50",
            ),
            positions=[position(quantity="0.4")],
            account={"cash": "99980", "equity": "100000"},
        )
        self.assertEqual(report.state, FillReconciliationState.WAITING_PARTIAL_FILL)
        self.assertEqual(report.remaining_quantity, "0.6")

    def test_invalid_partial_safe_mode(self):
        report = self.reconciler.reconcile(
            order=order(status="partially_filled", filled_quantity="0"),
            positions=[],
            account={},
        )
        self.assertTrue(report.safe_mode_engaged)

    def test_filled_reconciles(self):
        report = self.reconciler.reconcile(
            order=order(
                status="filled",
                filled_quantity="1",
                average_fill_price="50",
            ),
            positions=[position()],
            account={"cash": "99950", "equity": "100000"},
        )
        self.assertEqual(report.state, FillReconciliationState.FILLED_RECONCILED)
        self.assertTrue(report.new_order_allowed)
        self.assertEqual(report.issue_count, 0)

    def test_filled_quantity_mismatch(self):
        report = self.reconciler.reconcile(
            order=order(
                status="filled",
                filled_quantity="0.5",
                average_fill_price="50",
            ),
            positions=[position(quantity="0.5")],
            account={},
        )
        self.assertTrue(report.safe_mode_engaged)

    def test_position_quantity_mismatch(self):
        report = self.reconciler.reconcile(
            order=order(
                status="filled",
                filled_quantity="1",
                average_fill_price="50",
            ),
            positions=[position(quantity="0")],
            account={},
        )
        self.assertTrue(report.safe_mode_engaged)

    def test_average_price_mismatch(self):
        report = self.reconciler.reconcile(
            order=order(
                status="filled",
                filled_quantity="1",
                average_fill_price="50",
            ),
            positions=[position(average_entry_price="51")],
            account={},
        )
        self.assertTrue(report.safe_mode_engaged)

    def test_canceled_no_fill(self):
        report = self.reconciler.reconcile(
            order=order(status="canceled"),
            positions=[],
            account={},
        )
        self.assertEqual(report.state, FillReconciliationState.TERMINAL_NO_FILL)
        self.assertTrue(report.new_order_allowed)

    def test_canceled_after_partial_matches_position(self):
        report = self.reconciler.reconcile(
            order=order(
                status="canceled",
                filled_quantity="0.4",
                average_fill_price="50",
            ),
            positions=[position(quantity="0.4")],
            account={},
        )
        self.assertFalse(report.safe_mode_engaged)

    def test_canceled_after_partial_mismatch(self):
        report = self.reconciler.reconcile(
            order=order(status="canceled", filled_quantity="0.4"),
            positions=[position(quantity="0.2")],
            account={},
        )
        self.assertTrue(report.safe_mode_engaged)

    def test_unknown_status_safe_mode(self):
        report = self.reconciler.reconcile(
            order=order(status="mystery"),
            positions=[],
            account={},
        )
        self.assertEqual(report.state, FillReconciliationState.SAFE_MODE)
        self.assertFalse(report.new_order_allowed)

    def test_zero_write_counters(self):
        report = self.reconciler.reconcile(
            order=order(),
            positions=[],
            account={},
            network_requests_executed=3,
        )
        self.assertEqual(report.network_requests_executed, 3)
        self.assertEqual(report.write_requests_executed, 0)
        self.assertEqual(report.actual_paper_orders_submitted, 0)
        self.assertEqual(report.live_orders_submitted, 0)

    def test_json(self):
        report = self.reconciler.reconcile(
            order=order(),
            positions=[],
            account={},
        )
        self.assertEqual(
            report.to_json_dict()["state"],
            "WAITING_ACTIVE_ORDER",
        )


if __name__ == "__main__":
    unittest.main()
