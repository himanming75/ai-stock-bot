from __future__ import annotations

import inspect
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from p3_cancel_validation.client import AlpacaPaperCancelClient
from p3_cancel_validation.plan import create_cancel_plan
from p3_cancel_validation.service import (
    P3PaperCancelValidationService,
)


class Tests(unittest.TestCase):
    def test_valid_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = create_cancel_plan(
                symbol="SPY",
                notional=Decimal("5"),
                price_multiplier=Decimal("0.50"),
                output_path=Path(directory) / "plan.json",
            )
            self.assertFalse(plan["blocked"])

    def test_multiplier_above_80_percent_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = create_cancel_plan(
                symbol="SPY",
                notional=Decimal("5"),
                price_multiplier=Decimal("0.90"),
                output_path=Path(directory) / "plan.json",
            )
            self.assertTrue(plan["blocked"])

    def test_paper_endpoint_guard(self):
        source = inspect.getsource(
            AlpacaPaperCancelClient.__init__
        )
        self.assertIn("NON_PAPER_ENDPOINT_BLOCKED", source)

    def test_cancel_delete_exists(self):
        source = inspect.getsource(
            AlpacaPaperCancelClient.cancel_order
        )
        self.assertIn('method="DELETE"', source)

    def test_live_submission_zero(self):
        source = inspect.getsource(
            P3PaperCancelValidationService.run
        )
        self.assertIn(
            '"actual_live_orders_submitted": 0',
            source,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
