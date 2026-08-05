import inspect, tempfile, unittest
from pathlib import Path
from p3_reject_validation.client import AlpacaPaperRejectClient
from p3_reject_validation.plan import create_reject_plan
from p3_reject_validation.service import P3PaperRejectValidationService

class Tests(unittest.TestCase):
    def test_invalid_payload_has_qty_and_notional(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = create_reject_plan(Path(directory)/"plan.json")
            self.assertIn("qty", plan["payload"])
            self.assertIn("notional", plan["payload"])

    def test_expected_statuses(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = create_reject_plan(Path(directory)/"plan.json")
            self.assertEqual(plan["expected_http_statuses"], [400, 422])

    def test_paper_endpoint_guard(self):
        self.assertIn("NON_PAPER_ENDPOINT_BLOCKED", inspect.getsource(AlpacaPaperRejectClient.__init__))

    def test_no_successful_submission_contract(self):
        source = inspect.getsource(P3PaperRejectValidationService.run)
        self.assertIn('"actual_order_submission_performed": False', source)
        self.assertIn('"actual_paper_orders_submitted": 0', source)

    def test_live_zero(self):
        self.assertIn('"actual_live_orders_submitted": 0', inspect.getsource(P3PaperRejectValidationService.run))

if __name__ == "__main__": unittest.main(verbosity=2)
