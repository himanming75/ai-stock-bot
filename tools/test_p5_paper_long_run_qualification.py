from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from broker_integration.p5_models import QualificationPolicy
from broker_integration.p5_qualification import run_long_run_qualification


def policy(cycles=10, failures=0, consecutive=0):
    return QualificationPolicy(
        required_cycles=cycles,
        maximum_failed_cycles=failures,
        maximum_consecutive_failures=consecutive,
        require_restart_recovery=True,
        require_duplicate_protection=True,
        require_kill_switch_test=True,
        require_reconciliation_test=True,
        require_market_close_test=True,
        require_next_day_resume_test=True,
    )


class Tests(unittest.TestCase):
    def test_successful_long_run(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = run_long_run_qualification(
                policy=policy(100),
                cycle_runner=lambda n: {"status": "PASS"},
                checkpoint_path=base/"checkpoint.json",
                result_path=base/"result.json",
            )
        self.assertTrue(result["qualified"])
        self.assertEqual(result["metrics"]["successful_cycles"], 100)

    def test_failure_blocks(self):
        def runner(n):
            return {"status": "FAIL" if n == 3 else "PASS"}
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = run_long_run_qualification(
                policy=policy(10),
                cycle_runner=runner,
                checkpoint_path=base/"checkpoint.json",
                result_path=base/"result.json",
            )
        self.assertFalse(result["qualified"])

    def test_checkpoint_written(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            checkpoint = base/"checkpoint.json"
            run_long_run_qualification(
                policy=policy(5),
                cycle_runner=lambda n: {"status": "PASS"},
                checkpoint_path=checkpoint,
                result_path=base/"result.json",
            )
            self.assertTrue(checkpoint.exists())

    def test_fault_matrix_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = run_long_run_qualification(
                policy=policy(5),
                cycle_runner=lambda n: {"status": "PASS"},
                checkpoint_path=base/"checkpoint.json",
                result_path=base/"result.json",
            )
        self.assertTrue(result["fault_matrix"]["passed"])

    def test_offline_does_not_mark_actual_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = run_long_run_qualification(
                policy=policy(5),
                cycle_runner=lambda n: {"status": "PASS"},
                checkpoint_path=base/"checkpoint.json",
                result_path=base/"result.json",
            )
        self.assertFalse(result["actual_paper_long_run_qualified"])
        self.assertFalse(result["paper_complete"])

    def test_zero_orders(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = run_long_run_qualification(
                policy=policy(5),
                cycle_runner=lambda n: {"status": "PASS"},
                checkpoint_path=base/"checkpoint.json",
                result_path=base/"result.json",
            )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
