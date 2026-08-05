from __future__ import annotations
import unittest
from decimal import Decimal
from types import SimpleNamespace
from ai_execution_plan_bridge.service import ExecutionPlanBridgeService

class FakeExecution:
    def plan(self, **kwargs):
        return SimpleNamespace(
            side=kwargs["side"],
            order_type="limit",
            slice_count=2,
            limit_price=Decimal("501.00"),
            expected_slippage_bps=Decimal("3.00"),
            time_limit_seconds=120,
            blockers=(),
        )

class Tests(unittest.TestCase):
    def payload(self, approved=True):
        return {"bridge":{"decisions":[{
            "symbol":"QQQ",
            "approved":approved,
            "approved_notional":"3800.00"
        }]}}

    def config(self):
        return {
            "default_reference_prices":{"QQQ":"500"},
            "maximum_order_notional":"5000",
            "allow_fractional":True
        }

    def test_approved_decision_builds_plan(self):
        plans=ExecutionPlanBridgeService(FakeExecution()).build(self.payload(),self.config())
        self.assertEqual(len(plans),1)
        self.assertEqual(plans[0].quantity,Decimal("7.6000"))

    def test_unapproved_decision_skipped(self):
        plans=ExecutionPlanBridgeService(FakeExecution()).build(self.payload(False),self.config())
        self.assertEqual(plans,[])

    def test_missing_price_blocks(self):
        plans=ExecutionPlanBridgeService(FakeExecution()).build(
            self.payload(),{"default_reference_prices":{}}
        )
        self.assertTrue(plans[0].blocked)

    def test_no_order_side_effect(self):
        source=__import__("inspect").getsource(ExecutionPlanBridgeService.run_file)
        self.assertIn('"actual_order_submission_performed": False',source)

    def test_zero_orders(self):
        source=__import__("inspect").getsource(ExecutionPlanBridgeService.run_file)
        self.assertIn('"actual_paper_orders_submitted": 0',source)

if __name__=="__main__":
    unittest.main(verbosity=2)
