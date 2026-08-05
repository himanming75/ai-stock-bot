from __future__ import annotations
import inspect
import tempfile
import unittest
from pathlib import Path

from paper_order_ticket_builder.io import write_json
from paper_order_ticket_builder.service import (
    PaperOrderTicketBuilderService,
)

class Tests(unittest.TestCase):
    def inputs(self, root: Path, ready=True):
        planning = root / "planning.json"
        plan = {
            "plan_id": "execplan-1",
            "symbol": "SPY",
            "side": "BUY",
            "status": "READY_FOR_MANUAL_REVIEW",
            "child_orders": [
                {
                    "sequence": 1,
                    "symbol": "SPY",
                    "side": "BUY",
                    "planned_notional": "100",
                    "order_type": "limit",
                    "time_in_force": "day",
                },
                {
                    "sequence": 2,
                    "symbol": "SPY",
                    "side": "BUY",
                    "planned_notional": "100",
                    "order_type": "limit",
                    "time_in_force": "day",
                },
            ],
        }
        write_json(
            planning,
            {
                "status": "PASS" if ready else "INSUFFICIENT_INPUT",
                "execution_planning_fingerprint": "plan-fp",
                "ready_plans": [plan] if ready else [],
            },
        )
        market = root / "market.json"
        write_json(
            market,
            {
                "symbols": {
                    "SPY": {"latest_price": "500.00"}
                }
            },
        )
        policy = root / "policy.json"
        write_json(
            policy,
            {
                "max_ticket_notional": "500",
                "limit_offset_bps": "5",
                "extended_hours": False,
            },
        )
        registry = root / "registry.json"
        write_json(registry, {"idempotency_keys": []})
        return planning, market, policy, registry

    def evaluate(self, root, ready=True):
        paths = self.inputs(root, ready)
        return PaperOrderTicketBuilderService().evaluate(
            execution_planning_path=paths[0],
            market_path=paths[1],
            policy_path=paths[2],
            prior_ticket_registry_path=paths[3],
            output_dir=root / "out",
        )

    def test_builds_two_valid_tickets(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory))
            self.assertEqual(result["valid_ticket_count"], 2)
            self.assertEqual(
                result["valid_tickets"][0]["payload"]["symbol"],
                "SPY",
            )

    def test_blocked_planning_builds_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory), ready=False)
            self.assertEqual(result["ticket_count"], 0)
            self.assertEqual(result["status"], "INSUFFICIENT_INPUT")

    def test_ticket_has_idempotency_key(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory))
            self.assertTrue(
                result["valid_tickets"][0]["idempotency_key"]
            )

    def test_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.evaluate(root)
            self.assertTrue(
                (root / "out/paper_order_ticket_dashboard.json").exists()
            )
            self.assertTrue(
                (root / "out/paper_order_ticket_ledger.jsonl").exists()
            )

    def test_no_submission(self):
        source = inspect.getsource(PaperOrderTicketBuilderService)
        self.assertIn('"actual_broker_write_performed": False', source)
        self.assertIn('"actual_paper_orders_submitted": 0', source)
        self.assertIn('"actual_live_orders_submitted": 0', source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
