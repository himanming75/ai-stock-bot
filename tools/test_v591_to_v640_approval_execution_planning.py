from __future__ import annotations
import inspect
import tempfile
import unittest
from pathlib import Path

from approval_execution_planning.io import write_json
from approval_execution_planning.service import (
    ApprovalExecutionPlanningService,
)

class Tests(unittest.TestCase):
    def inputs(self, root: Path, approval_status="APPROVED_FOR_SEPARATE_SUBMISSION_STAGE"):
        allocation = root / "allocation.json"
        write_json(allocation, {
            "portfolio_intelligence_fingerprint": "pf-1",
            "allocation_queue": [{
                "symbol": "SPY",
                "side": "BUY",
                "proposed_notional": "300",
                "status": "READY",
            }],
        })
        approval = root / "approval.json"
        write_json(approval, {
            "status": approval_status,
            "audit_record_hash": "approval-1",
        })
        market = root / "market.json"
        write_json(market, {
            "symbols": {
                "SPY": {
                    "is_open": True,
                    "estimated_spread_bps": "2",
                    "estimated_slippage_bps": "3",
                    "average_daily_dollar_volume": "1000000000",
                    "volatility_percent": "1.5",
                }
            }
        })
        policy = root / "policy.json"
        write_json(policy, {
            "require_market_open": True,
            "max_order_notional": "500",
            "max_spread_bps": "25",
            "minimum_daily_dollar_volume": "10000000",
            "max_slippage_bps": "20",
            "max_volatility_percent": "5",
            "submission_enabled": False,
            "child_order_count": 3,
            "default_order_type": "limit",
            "time_in_force": "day",
        })
        prior = root / "prior.json"
        write_json(prior, {"duplicate_keys": []})
        return allocation, approval, market, policy, prior

    def evaluate(self, root, approval_status="APPROVED_FOR_SEPARATE_SUBMISSION_STAGE"):
        paths = self.inputs(root, approval_status)
        return ApprovalExecutionPlanningService().evaluate(
            allocation_path=paths[0],
            approval_path=paths[1],
            market_path=paths[2],
            policy_path=paths[3],
            prior_plans_path=paths[4],
            output_dir=root / "out",
        )

    def test_ready_for_manual_review(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory))
            self.assertEqual(
                result["ready_for_manual_review_count"], 1
            )
            self.assertEqual(
                result["ready_plans"][0]["child_order_count"], 3
            )

    def test_approval_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory), "BLOCKED")
            self.assertEqual(result["ready_for_manual_review_count"], 0)

    def test_missing_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, approval, market, policy, prior = self.inputs(root)
            result = ApprovalExecutionPlanningService().evaluate(
                allocation_path=root / "missing.json",
                approval_path=approval,
                market_path=market,
                policy_path=policy,
                prior_plans_path=prior,
                output_dir=root / "out",
            )
            self.assertEqual(result["status"], "INSUFFICIENT_INPUT")

    def test_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.evaluate(root)
            self.assertTrue(
                (root / "out/execution_planning_dashboard.json").exists()
            )
            self.assertTrue(
                (root / "out/execution_plan_ledger.jsonl").exists()
            )

    def test_no_submission(self):
        source = inspect.getsource(
            ApprovalExecutionPlanningService
        )
        self.assertIn('"actual_order_ticket_created": False', source)
        self.assertIn('"actual_paper_orders_submitted": 0', source)
        self.assertIn('"actual_live_orders_submitted": 0', source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
