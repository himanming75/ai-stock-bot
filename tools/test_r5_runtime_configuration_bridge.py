from __future__ import annotations
from decimal import Decimal
import unittest

from configuration_profiles.models import TradingProfile
from runtime_configuration.binding import (
    bind_profile_to_runtime,
    build_order_router_binding,
    build_risk_binding,
    build_strategy_binding,
)
from runtime_configuration.environment import build_environment_preview


class Tests(unittest.TestCase):
    def profile(self):
        return TradingProfile(
            profile_name="paper_ultra_short",
            broker_mode="paper",
            horizon="ultra_short",
            allowed_symbols=("AAPL", "MSFT", "SPY"),
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

    def test_profile_binds(self):
        runtime = bind_profile_to_runtime(self.profile())
        self.assertEqual(runtime.horizon, "ultra_short")
        self.assertFalse(runtime.broker_write_enabled)

    def test_strategy_binding_preserves_allocation(self):
        runtime = bind_profile_to_runtime(self.profile())
        binding = build_strategy_binding(runtime)
        self.assertTrue(binding["allocation_enabled"])
        self.assertFalse(binding["strategy_execution_enabled"])

    def test_risk_binding_preserves_limits(self):
        runtime = bind_profile_to_runtime(self.profile())
        binding = build_risk_binding(runtime)
        self.assertEqual(binding["maximum_order_notional"], "10")
        self.assertFalse(binding["broker_submission_enabled"])

    def test_order_router_binding_is_read_only(self):
        runtime = bind_profile_to_runtime(self.profile())
        binding = build_order_router_binding(runtime)
        self.assertFalse(binding["broker_network_enabled"])
        self.assertFalse(binding["broker_write_enabled"])

    def test_environment_preview_does_not_enable_write(self):
        runtime = bind_profile_to_runtime(self.profile())
        env = build_environment_preview(runtime)
        self.assertEqual(env["PAPER_BROKER_WRITE_ENABLED"], "false")
        self.assertEqual(
            env["PAPER_AUTOMATIC_ORDER_SUBMISSION_ENABLED"],
            "false",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
