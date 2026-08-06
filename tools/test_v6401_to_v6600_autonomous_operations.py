from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from autonomous_operations.circuit import (
    CircuitBreaker,
)
from autonomous_operations.fixtures import (
    CRITICAL_MODULES,
    HEALTHY_MODULES,
)
from autonomous_operations.orchestrator import (
    AutonomousOperationsOrchestrator,
)
from autonomous_operations.service import (
    AutonomousOperationsCertificationService,
)


class Tests(unittest.TestCase):
    def orchestrator(self, root: Path):
        return AutonomousOperationsOrchestrator(
            checkpoint_path=root / "checkpoint.json",
            ledger_path=root / "ledger.jsonl",
        )

    def test_healthy_cycle(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.orchestrator(
                Path(directory)
            ).run_cycle(
                module_health=HEALTHY_MODULES,
                market_open=True,
                requested_action="BUY",
            )
            self.assertEqual(
                result["cycle_result"]["status"],
                "PASS",
            )

    def test_market_closed_wait(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.orchestrator(
                Path(directory)
            ).run_cycle(
                module_health=HEALTHY_MODULES,
                market_open=False,
                requested_action="BUY",
            )
            self.assertEqual(
                result["cycle_result"]["final_action"],
                "WAIT",
            )

    def test_critical_emergency_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.orchestrator(
                Path(directory)
            ).run_cycle(
                module_health=CRITICAL_MODULES,
                market_open=True,
                requested_action="BUY",
            )
            self.assertEqual(
                result["cycle_result"]["final_action"],
                "ALL_STOP",
            )

    def test_circuit_breaker(self):
        circuit = CircuitBreaker(
            failure_threshold=3,
            recovery_success_threshold=2,
        )
        circuit.record_failure()
        circuit.record_failure()
        self.assertEqual(
            circuit.record_failure(),
            "OPEN",
        )
        self.assertEqual(
            circuit.record_success(),
            "HALF_OPEN",
        )
        self.assertEqual(
            circuit.record_success(),
            "CLOSED",
        )

    def test_restart_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = self.orchestrator(root)
            first.run_cycle(
                module_health=CRITICAL_MODULES,
                market_open=True,
                requested_action="BUY",
            )
            restored = self.orchestrator(
                root
            ).restore()
            self.assertEqual(
                restored["last_status"],
                "EMERGENCY_STOP",
            )

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                AutonomousOperationsCertificationService()
                .evaluate(
                    output_dir=Path(directory)
                )
            )
            self.assertEqual(
                result["status"],
                "PASS",
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                AutonomousOperationsCertificationService()
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
