from __future__ import annotations
import inspect
import tempfile
import unittest
from pathlib import Path

from paper_recovery_retry.io import write_json
from paper_recovery_retry.service import PaperRecoveryRetryService


class Tests(unittest.TestCase):
    def inputs(self, root: Path, attempts=0):
        retry = root / "retry.json"
        write_json(
            retry,
            {
                "items": [
                    {
                        "submission_id": "submit-1",
                        "ticket_id": "ticket-1",
                        "reason": "RATE_LIMITED",
                    }
                ]
            },
        )
        recovery = root / "recovery.json"
        write_json(
            recovery,
            {
                "items": [
                    {
                        "submission_id": "submit-2",
                        "ticket_id": "ticket-2",
                        "state": "AWAITING_MANUAL_RECOVERY_REVIEW",
                    }
                ]
            },
        )
        checkpoint = root / "checkpoint.json"
        write_json(
            checkpoint,
            {"attempts": {"submit-1": attempts}},
        )
        policy = root / "policy.json"
        write_json(
            policy,
            {
                "maximum_attempts": 3,
                "base_backoff_seconds": 5,
                "maximum_backoff_seconds": 60,
                "automatic_retry_enabled": False,
                "automatic_recovery_enabled": False,
            },
        )
        return retry, recovery, checkpoint, policy

    def evaluate(self, root: Path, attempts=0):
        paths = self.inputs(root, attempts)
        return PaperRecoveryRetryService().evaluate(
            retry_queue_path=paths[0],
            recovery_queue_path=paths[1],
            checkpoint_path=paths[2],
            policy_path=paths[3],
            output_dir=root / "out",
        )

    def test_retry_plan_created(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory))
            self.assertEqual(result["manual_retry_plan_count"], 1)
            self.assertEqual(
                result["retry_plans"][0]["backoff_seconds"], 5
            )

    def test_dead_letter_after_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory), attempts=3)
            self.assertEqual(result["dead_letter_count"], 1)

    def test_manual_recovery_created(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory))
            self.assertEqual(result["manual_recovery_count"], 1)

    def test_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.evaluate(root)
            self.assertTrue(
                (root / "out/paper_recovery_retry_dashboard.json").exists()
            )
            self.assertTrue(
                (root / "out/manual_retry_plan_ledger.jsonl").exists()
            )

    def test_zero_order_contract(self):
        source = inspect.getsource(PaperRecoveryRetryService)
        self.assertIn('"actual_broker_write_performed": False', source)
        self.assertIn('"actual_paper_orders_submitted": 0', source)
        self.assertIn('"actual_live_orders_submitted": 0', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
