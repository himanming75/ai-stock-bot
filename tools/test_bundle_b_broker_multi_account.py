from __future__ import annotations
from decimal import Decimal
import unittest

from broker_platform.accounts import validate_account_registry
from broker_platform.adapters import (
    AlpacaPreparedAdapter,
    build_default_registry,
)
from broker_platform.models import AccountDefinition


class Tests(unittest.TestCase):
    def account(self, **overrides):
        value = {
            "account_id": "a",
            "broker_id": "alpaca",
            "broker_mode": "paper",
            "profile_name": "paper_ultra_short",
            "enabled": True,
            "allocation_weight": Decimal("1"),
            "maximum_account_notional": Decimal("10"),
            "credential_vault_mode": "paper",
            "tags": (),
        }
        value.update(overrides)
        return AccountDefinition(**value)

    def test_account_valid(self):
        self.assertTrue(self.account().validate()["valid"])

    def test_duplicate_account_ids_rejected(self):
        result = validate_account_registry([
            self.account(),
            self.account(),
        ])
        self.assertFalse(result["valid"])

    def test_live_enabled_account_rejected_in_preparation(self):
        result = validate_account_registry([
            self.account(
                account_id="live",
                broker_mode="live",
                credential_vault_mode="live",
                enabled=True,
            )
        ])
        self.assertFalse(result["valid"])

    def test_alpaca_submit_disabled(self):
        adapter = AlpacaPreparedAdapter()
        with self.assertRaises(RuntimeError):
            adapter.submit_order({})

    def test_four_adapters_registered(self):
        matrix = build_default_registry().capability_matrix()
        self.assertEqual(matrix["broker_count"], 4)
        self.assertFalse(matrix["actual_write_enabled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
