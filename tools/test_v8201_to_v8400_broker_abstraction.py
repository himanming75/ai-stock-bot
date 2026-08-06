from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from broker_abstraction.capabilities import (
    get_capabilities,
)
from broker_abstraction.factory import (
    BrokerFactory,
)
from broker_abstraction.router import (
    ReadOnlyBrokerRouter,
)
from broker_abstraction.service import (
    BrokerAbstractionCertificationService,
)


class Tests(unittest.TestCase):
    def test_capabilities(self):
        self.assertTrue(
            get_capabilities("ETRADE")["options"]
        )
        self.assertFalse(
            get_capabilities("ETRADE")["write_enabled"]
        )

    def test_factory(self):
        adapter = BrokerFactory.create(
            "ALPACA",
            snapshot={},
        )
        self.assertEqual(
            adapter.broker_name,
            "ALPACA",
        )

    def test_router_write_block(self):
        router = ReadOnlyBrokerRouter()
        with self.assertRaises(PermissionError):
            router.submit_order()
        with self.assertRaises(PermissionError):
            router.cancel_order()

    def test_certification(self):
        with tempfile.TemporaryDirectory() as d:
            result = (
                BrokerAbstractionCertificationService()
                .evaluate(output_dir=Path(d))
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(
                result["snapshot"]["totals"]["brokers"],
                2,
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as d:
            result = (
                BrokerAbstractionCertificationService()
                .evaluate(output_dir=Path(d))
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
