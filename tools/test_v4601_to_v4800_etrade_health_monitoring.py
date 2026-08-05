from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from multi_broker_etrade_health.fixtures import (
    CRITICAL_FIXTURE,
    DEGRADED_FIXTURE,
    HEALTHY_FIXTURE,
)
from multi_broker_etrade_health.service import (
    ETradeHealthMonitoringService,
)


class Tests(unittest.TestCase):
    def setUp(self):
        self.service = ETradeHealthMonitoringService()

    def test_healthy_case(self):
        result = self.service.evaluate_case(
            "HEALTHY",
            HEALTHY_FIXTURE,
        )
        self.assertEqual(
            result["routing_decision"]["mode"],
            "READ_ONLY_NORMAL",
        )

    def test_degraded_case(self):
        result = self.service.evaluate_case(
            "DEGRADED",
            DEGRADED_FIXTURE,
        )
        self.assertTrue(
            result["routing_decision"]["read_allowed"]
        )
        self.assertFalse(
            result["routing_decision"]["write_allowed"]
        )

    def test_critical_case(self):
        result = self.service.evaluate_case(
            "CRITICAL",
            CRITICAL_FIXTURE,
        )
        self.assertEqual(
            result["routing_decision"]["mode"],
            "FAILSAFE_BLOCKED",
        )
        self.assertFalse(
            result["routing_decision"]["read_allowed"]
        )

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.service.evaluate(
                output_dir=Path(directory)
            )
            self.assertEqual(result["status"], "PASS")

    def test_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.service.evaluate(output_dir=root)
            self.assertTrue(
                (root / "etrade_health_dashboard.json").exists()
            )
            self.assertTrue(
                (
                    root
                    / "etrade_health_monitoring_ledger.jsonl"
                ).exists()
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.service.evaluate(
                output_dir=Path(directory)
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
