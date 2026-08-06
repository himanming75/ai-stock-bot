from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from trading_configuration.api import (
    TradingConfigurationService,
)
from trading_configuration.defaults import (
    new_draft,
)
from trading_configuration.service import (
    TradingConfigurationCertificationService,
)
from trading_configuration.validation import (
    validate_draft,
)


class Tests(unittest.TestCase):
    def test_read_only_forces_zero_capital(self):
        result = validate_draft(new_draft())
        self.assertEqual(
            result["capital_limit"],
            0,
        )
        self.assertEqual(
            result["profile"]["max_positions"],
            0,
        )

    def test_activation_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            service = TradingConfigurationService(
                draft_path=root / "draft.json",
                ledger_path=root / "ledger.jsonl",
            )
            with self.assertRaises(
                PermissionError
            ):
                service.activate({})

    def test_certification(self):
        with tempfile.TemporaryDirectory() as d:
            result = (
                TradingConfigurationCertificationService()
                .evaluate(output_dir=Path(d))
            )
            self.assertEqual(
                result["status"],
                "PASS",
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as d:
            result = (
                TradingConfigurationCertificationService()
                .evaluate(output_dir=Path(d))
            )
            self.assertFalse(
                result[
                    "actual_configuration_activated"
                ]
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
