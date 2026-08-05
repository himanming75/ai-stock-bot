from __future__ import annotations
import inspect
import tempfile
import unittest
from pathlib import Path

from paper_submit_engine.io import write_json
from paper_submit_engine.service import PaperSubmitEngineService


class Tests(unittest.TestCase):
    def inputs(self, root: Path, status_code=201):
        queue = root / "queue.json"
        write_json(
            queue,
            {
                "submission_enabled": False,
                "items": [
                    {
                        "ticket_id": "ticket-1",
                        "idempotency_key": "idem-1",
                        "status": "APPROVED_FOR_SEPARATE_SUBMISSION_STAGE",
                        "broker_request": {
                            "request": {
                                "method": "POST",
                                "url": "https://paper-api.alpaca.markets/v2/orders",
                                "headers": {
                                    "Content-Type": "application/json",
                                    "Idempotency-Key": "idem-1",
                                },
                                "json": {
                                    "symbol": "SPY",
                                    "side": "buy",
                                    "type": "limit",
                                    "time_in_force": "day",
                                    "notional": "100",
                                    "limit_price": "500",
                                },
                                "submission_enabled": False,
                                "broker_write_allowed": False,
                            }
                        },
                    }
                ],
            },
        )
        policy = root / "policy.json"
        write_json(
            policy,
            {
                "engine_mode": "dry_run",
                "network_enabled": False,
                "broker_write_enabled": False,
                "paper_submission_enabled": False,
                "live_submission_enabled": False,
            },
        )
        fixture = root / "fixture.json"
        write_json(
            fixture,
            {
                "default_response": {
                    "status_code": status_code,
                    "body": {"id": "simulated-order"},
                }
            },
        )
        return queue, policy, fixture

    def evaluate(self, root, status_code=201):
        paths = self.inputs(root, status_code)
        return PaperSubmitEngineService().evaluate(
            approved_queue_path=paths[0],
            policy_path=paths[1],
            simulated_response_path=paths[2],
            output_dir=root / "out",
        )

    def test_dry_run_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory))
            self.assertEqual(result["dry_run_ready_count"], 1)

    def test_rate_limit_creates_retry_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory), 429)
            self.assertEqual(result["retry_queue_count"], 1)

    def test_no_credentials_or_network(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory))
            self.assertFalse(result["credentials_loaded"])
            self.assertFalse(result["actual_external_network_used"])

    def test_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.evaluate(root)
            self.assertTrue(
                (root / "out/paper_submit_dashboard.json").exists()
            )
            self.assertTrue(
                (root / "out/paper_submit_attempt_ledger.jsonl").exists()
            )

    def test_zero_order_contract(self):
        source = inspect.getsource(PaperSubmitEngineService)
        self.assertIn('"actual_broker_write_performed": False', source)
        self.assertIn('"actual_paper_orders_submitted": 0', source)
        self.assertIn('"actual_live_orders_submitted": 0', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
