from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from dual_account_safety.fixtures import (
    ALPACA_PAPER,
    ETRADE_PRIMARY,
)
from dual_account_safety.models import (
    RouteRequest,
)
from dual_account_safety.registry import (
    AccountRegistry,
)
from dual_account_safety.routing import (
    SafeAccountRouter,
)
from dual_account_safety.service import (
    DualAccountSafetyCertificationService,
)


class Tests(unittest.TestCase):
    def registry(self):
        registry = AccountRegistry()
        registry.register(ALPACA_PAPER)
        registry.register(ETRADE_PRIMARY)
        return registry

    def test_two_account_registry(self):
        self.assertEqual(
            len(self.registry().all()),
            2,
        )

    def test_cross_broker_misroute_blocked(self):
        decision = SafeAccountRouter(
            self.registry()
        ).decide(
            RouteRequest(
                account_key="ETRADE_PRIMARY",
                broker="ALPACA",
                environment="PRODUCTION",
                operation="ACCOUNT_READ",
            )
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(
            decision.reason,
            "BROKER_MISMATCH",
        )

    def test_etrade_write_blocked(self):
        decision = SafeAccountRouter(
            self.registry()
        ).decide(
            RouteRequest(
                account_key="ETRADE_PRIMARY",
                broker="ETRADE",
                environment="PRODUCTION",
                operation="ORDER_SUBMIT",
            )
        )
        self.assertFalse(decision.allowed)

    def test_etrade_read_pending_validation_blocked(self):
        decision = SafeAccountRouter(
            self.registry()
        ).decide(
            RouteRequest(
                account_key="ETRADE_PRIMARY",
                broker="ETRADE",
                environment="PRODUCTION",
                operation="ACCOUNT_READ",
            )
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(
            decision.reason,
            "ACTUAL_CONNECTION_NOT_VALIDATED",
        )

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                DualAccountSafetyCertificationService()
                .evaluate(
                    output_dir=Path(directory)
                )
            )
            self.assertEqual(
                result["status"],
                "PASS",
            )
            self.assertTrue(
                result[
                    "future_multi_account_extension_ready"
                ]
            )

    def test_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            DualAccountSafetyCertificationService().evaluate(
                output_dir=root
            )
            self.assertTrue(
                (
                    root
                    / "dual_account_extension_contract.json"
                ).exists()
            )
            self.assertTrue(
                (
                    root
                    / "dual_account_safety_ledger.jsonl"
                ).exists()
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                DualAccountSafetyCertificationService()
                .evaluate(
                    output_dir=Path(directory)
                )
            )
            self.assertFalse(
                result[
                    "actual_broker_write_performed"
                ]
            )
            self.assertEqual(
                result[
                    "actual_paper_orders_submitted"
                ],
                0,
            )
            self.assertEqual(
                result[
                    "actual_live_orders_submitted"
                ],
                0,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
