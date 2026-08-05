from __future__ import annotations
from decimal import Decimal
import unittest

from configuration_profiles.models import TradingProfile


class Tests(unittest.TestCase):
    def valid_profile(self):
        return TradingProfile(
            profile_name="paper_day",
            broker_mode="paper",
            horizon="day",
            allowed_symbols=("AAPL", "SPY"),
            allowed_order_types=("market", "limit"),
            time_in_force="day",
            maximum_order_notional=Decimal("10"),
            maximum_daily_orders=3,
            maximum_daily_loss=Decimal("10"),
            maximum_gross_exposure=Decimal("30"),
            maximum_symbol_exposure=Decimal("10"),
            require_market_open=True,
            allocation_enabled=True,
            multi_account_enabled=False,
            enabled=True,
        )

    def test_valid_profile(self):
        self.assertTrue(self.valid_profile().validate()["valid"])

    def test_invalid_horizon(self):
        profile = self.valid_profile()
        object.__setattr__(profile, "horizon", "invalid")
        self.assertFalse(profile.validate()["valid"])

    def test_symbol_exposure_cannot_exceed_gross(self):
        profile = self.valid_profile()
        object.__setattr__(
            profile,
            "maximum_symbol_exposure",
            Decimal("31"),
        )
        self.assertFalse(profile.validate()["valid"])

    def test_allocation_feature_preserved(self):
        result = self.valid_profile().validate()
        self.assertTrue(
            result["checks"]["allocation_feature_preserved"]
        )

    def test_multi_account_feature_preserved(self):
        result = self.valid_profile().validate()
        self.assertTrue(
            result["checks"]["multi_account_feature_preserved"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
