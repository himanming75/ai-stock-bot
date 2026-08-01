from __future__ import annotations

from decimal import Decimal
import unittest

from autonomous_paper_runtime import (
    AutonomousPaperReadReconciler,
    ReconciliationPolicy,
    ReconciliationStatus,
)


def actual_snapshot(**overrides):
    value = {
        "cash": "100000",
        "equity": "100000",
        "position_count": 0,
        "symbols_held": [],
        "open_order_count": 1,
    }
    value.update(overrides)
    return value


def internal_portfolio(**overrides):
    value = {
        "cash": "100000",
        "equity": "100000",
        "positions": [],
    }
    value.update(overrides)
    return value


def internal_recovery(**overrides):
    value = {
        "expected_snapshot_generation": 5,
        "actual_snapshot_generation": 5,
    }
    value.update(overrides)
    return value


def internal_runtime(**overrides):
    value = {
        "runtime_state": "READY",
        "open_order_count": 1,
    }
    value.update(overrides)
    return value


class AutonomousPaperReadReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.reconciler = AutonomousPaperReadReconciler()

    def test_all_matched(self):
        report = self.reconciler.reconcile(
            actual_snapshot=actual_snapshot(),
            internal_portfolio=internal_portfolio(),
            internal_recovery=internal_recovery(),
            internal_runtime=internal_runtime(),
        )
        self.assertEqual(report.status, ReconciliationStatus.MATCHED)
        self.assertFalse(report.safe_mode_engaged)
        self.assertTrue(report.autonomous_order_allowed)

    def test_cash_mismatch_blocks(self):
        report = self.reconciler.reconcile(
            actual_snapshot=actual_snapshot(cash="99999"),
            internal_portfolio=internal_portfolio(),
            internal_recovery=internal_recovery(),
            internal_runtime=internal_runtime(),
        )
        self.assertTrue(report.safe_mode_engaged)
        self.assertIn("CASH_MISMATCH", [item.code for item in report.issues])

    def test_cash_tolerance(self):
        reconciler = AutonomousPaperReadReconciler(
            policy=ReconciliationPolicy(cash_tolerance=Decimal("0.05"))
        )
        report = reconciler.reconcile(
            actual_snapshot=actual_snapshot(cash="100000.04"),
            internal_portfolio=internal_portfolio(),
            internal_recovery=internal_recovery(),
            internal_runtime=internal_runtime(),
        )
        self.assertTrue(report.cash_matched)

    def test_equity_mismatch_blocks(self):
        report = self.reconciler.reconcile(
            actual_snapshot=actual_snapshot(equity="100100"),
            internal_portfolio=internal_portfolio(),
            internal_recovery=internal_recovery(),
            internal_runtime=internal_runtime(),
        )
        self.assertTrue(report.safe_mode_engaged)

    def test_position_count_mismatch(self):
        report = self.reconciler.reconcile(
            actual_snapshot=actual_snapshot(position_count=1, symbols_held=["AAPL"]),
            internal_portfolio=internal_portfolio(),
            internal_recovery=internal_recovery(),
            internal_runtime=internal_runtime(),
        )
        self.assertFalse(report.position_count_matched)
        self.assertTrue(report.safe_mode_engaged)

    def test_position_symbol_mismatch(self):
        report = self.reconciler.reconcile(
            actual_snapshot=actual_snapshot(position_count=1, symbols_held=["SPY"]),
            internal_portfolio=internal_portfolio(
                positions=[{"symbol": "AAPL", "quantity": "1"}]
            ),
            internal_recovery=internal_recovery(),
            internal_runtime=internal_runtime(),
        )
        self.assertFalse(report.position_symbols_matched)

    def test_open_order_mismatch_blocks(self):
        report = self.reconciler.reconcile(
            actual_snapshot=actual_snapshot(open_order_count=1),
            internal_portfolio=internal_portfolio(),
            internal_recovery=internal_recovery(),
            internal_runtime=internal_runtime(open_order_count=0),
        )
        self.assertTrue(report.safe_mode_engaged)
        self.assertIn("OPEN_ORDER_COUNT_MISMATCH", [x.code for x in report.issues])

    def test_open_order_nonblocking_policy(self):
        policy = ReconciliationPolicy(block_on_open_order_mismatch=False)
        report = AutonomousPaperReadReconciler(policy=policy).reconcile(
            actual_snapshot=actual_snapshot(open_order_count=1),
            internal_portfolio=internal_portfolio(),
            internal_recovery=internal_recovery(),
            internal_runtime=internal_runtime(open_order_count=0),
        )
        self.assertEqual(report.status, ReconciliationStatus.MISMATCH)
        self.assertFalse(report.safe_mode_engaged)

    def test_recovery_generation_mismatch(self):
        report = self.reconciler.reconcile(
            actual_snapshot=actual_snapshot(),
            internal_portfolio=internal_portfolio(),
            internal_recovery=internal_recovery(actual_snapshot_generation=4),
            internal_runtime=internal_runtime(),
        )
        self.assertFalse(report.recovery_generation_matched)
        self.assertTrue(report.safe_mode_engaged)

    def test_runtime_state_mismatch(self):
        report = self.reconciler.reconcile(
            actual_snapshot=actual_snapshot(),
            internal_portfolio=internal_portfolio(),
            internal_recovery=internal_recovery(),
            internal_runtime=internal_runtime(runtime_state="RUNNING"),
        )
        self.assertFalse(report.runtime_state_matched)
        self.assertTrue(report.safe_mode_engaged)

    def test_multiple_mismatches(self):
        report = self.reconciler.reconcile(
            actual_snapshot=actual_snapshot(
                cash="90000",
                equity="95000",
                position_count=1,
                symbols_held=["AAPL"],
                open_order_count=2,
            ),
            internal_portfolio=internal_portfolio(),
            internal_recovery=internal_recovery(actual_snapshot_generation=3),
            internal_runtime=internal_runtime(
                runtime_state="RUNNING",
                open_order_count=0,
            ),
        )
        self.assertGreaterEqual(report.blocking_issue_count, 6)

    def test_zero_network_and_orders(self):
        report = self.reconciler.reconcile(
            actual_snapshot=actual_snapshot(),
            internal_portfolio=internal_portfolio(),
            internal_recovery=internal_recovery(),
            internal_runtime=internal_runtime(),
        )
        self.assertEqual(report.network_requests_executed, 0)
        self.assertEqual(report.write_requests_executed, 0)
        self.assertEqual(report.actual_paper_orders_submitted, 0)
        self.assertEqual(report.live_orders_submitted, 0)

    def test_json_serialization(self):
        report = self.reconciler.reconcile(
            actual_snapshot=actual_snapshot(),
            internal_portfolio=internal_portfolio(),
            internal_recovery=internal_recovery(),
            internal_runtime=internal_runtime(),
        )
        raw = report.to_json_dict()
        self.assertEqual(raw["status"], "MATCHED")
        self.assertEqual(raw["issues"], [])

    def test_policy_validation(self):
        with self.assertRaises(ValueError):
            ReconciliationPolicy(cash_tolerance=Decimal("-0.01")).validate()


if __name__ == "__main__":
    unittest.main()
