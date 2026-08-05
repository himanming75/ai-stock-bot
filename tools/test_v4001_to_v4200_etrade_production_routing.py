from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from multi_broker_etrade_routing.fixtures import (
    ACCOUNTS,
)
from multi_broker_etrade_routing.policy import (
    ProductionReadOnlyPolicy,
)
from multi_broker_etrade_routing.routing import (
    ETradeAccountRouter,
)
from multi_broker_etrade_routing.service import (
    ETradeProductionRoutingCertificationService,
)


class Tests(unittest.TestCase):
    def policy(self):
        return ProductionReadOnlyPolicy(
            production_read_enabled=False,
            broker_write_enabled=False,
            order_submission_enabled=False,
            order_cancel_enabled=False,
            require_explicit_environment_ack=True,
            allowed_account_id_keys=(
                "individual-brokerage-key",
                "stock-plan-key",
            ),
            default_account_id_key=(
                "individual-brokerage-key"
            ),
        )

    def test_production_guard(self):
        with self.assertRaises(PermissionError):
            self.policy().assert_production_read_allowed()

    def test_account_registry(self):
        router = ETradeAccountRouter(
            policy=self.policy(),
            aliases={
                "individual-brokerage-key": "PRIMARY",
                "stock-plan-key": "STOCK_PLAN",
            },
        )
        registry = router.build_registry(ACCOUNTS)
        self.assertEqual(len(registry), 3)
        self.assertEqual(
            registry[0].alias,
            "PRIMARY",
        )

    def test_default_selection(self):
        router = ETradeAccountRouter(
            policy=self.policy()
        )
        registry = router.build_registry(ACCOUNTS)
        selected = router.select(registry)
        self.assertEqual(
            selected.account_id_key,
            "individual-brokerage-key",
        )

    def test_unauthorized_account_blocked(self):
        with self.assertRaises(PermissionError):
            self.policy().assert_account_allowed(
                "unauthorized"
            )

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                ETradeProductionRoutingCertificationService()
                .evaluate(
                    output_dir=Path(directory)
                )
            )
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(
                result["production_network_read_performed"]
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                ETradeProductionRoutingCertificationService()
                .evaluate(
                    output_dir=Path(directory)
                )
            )
            self.assertFalse(
                result["actual_broker_write_performed"]
            )
            self.assertEqual(
                result["actual_paper_orders_submitted"],
                0,
            )
            self.assertEqual(
                result["actual_live_orders_submitted"],
                0,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
