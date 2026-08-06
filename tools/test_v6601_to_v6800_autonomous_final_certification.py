from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from autonomous_final_certification.checklists import (
    platform_readiness_checks,
    validation_gates,
)
from autonomous_final_certification.performance import (
    evaluate_fixture_metrics,
)
from autonomous_final_certification.service import (
    AutonomousPlatformFinalCertificationService,
)


class Tests(unittest.TestCase):
    def test_readiness_checks(self):
        checks = platform_readiness_checks()
        self.assertGreaterEqual(len(checks), 10)

    def test_validation_gates(self):
        gates = validation_gates()
        self.assertTrue(
            any(
                item.name == "ETRADE_SANDBOX_READ"
                and item.status == "BLOCKED"
                for item in gates
            )
        )

    def test_fixture_performance(self):
        result = evaluate_fixture_metrics()
        self.assertEqual(
            result["fixture_performance_status"],
            "PASS",
        )

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                AutonomousPlatformFinalCertificationService()
                .evaluate(
                    output_dir=Path(directory)
                )
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(
                result["phase_5_status"],
                "STRUCTURALLY_COMPLETE",
            )

    def test_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            AutonomousPlatformFinalCertificationService().evaluate(
                output_dir=root
            )
            self.assertTrue(
                (
                    root
                    / "autonomous_paper_intraday_handoff.json"
                ).exists()
            )
            self.assertTrue(
                (
                    root
                    / "autonomous_platform_final_certification_ledger.jsonl"
                ).exists()
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                AutonomousPlatformFinalCertificationService()
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
