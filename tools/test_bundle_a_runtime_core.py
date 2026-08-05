from __future__ import annotations
from decimal import Decimal
import unittest

from runtime_core.allocation import CapitalAllocationEngine
from runtime_core.models import Signal
from runtime_core.plugins import (
    DeterministicFixtureStrategy,
    StrategyRegistry,
)
from runtime_core.portfolio import PortfolioExposureManager
from runtime_core.risk import RuntimeRiskEvaluator


RUNTIME = {
    "allowed_symbols": ["AAPL", "MSFT", "SPY"],
    "allowed_order_types": ["market", "limit"],
    "time_in_force": "day",
    "require_market_open": True,
    "allocation_enabled": True,
    "multi_account_enabled": False,
    "broker_network_enabled": False,
    "broker_write_enabled": False,
    "risk_limits": {
        "maximum_order_notional": "10",
        "maximum_daily_orders": 3,
        "maximum_daily_loss": "10",
        "maximum_gross_exposure": "30",
        "maximum_symbol_exposure": "10",
    },
}


class Tests(unittest.TestCase):
    def signal(self, side="buy"):
        return Signal(
            strategy_id="fixture",
            symbol="AAPL",
            side=side,
            strength=Decimal("0.8"),
            reference_price=Decimal("200"),
            reason="test",
        )

    def test_registry_rejects_duplicate(self):
        registry = StrategyRegistry()
        plugin = DeterministicFixtureStrategy()
        registry.register(plugin)
        with self.assertRaises(ValueError):
            registry.register(plugin)

    def test_risk_approves_valid_signal_without_submission(self):
        result = RuntimeRiskEvaluator().evaluate(
            signal=self.signal(),
            runtime_snapshot=RUNTIME,
            daily_state={"order_count": 0, "realized_loss": "0"},
        )
        self.assertTrue(result["approved"])
        self.assertFalse(result["broker_submission_allowed"])

    def test_allocation_respects_order_limit(self):
        result = CapitalAllocationEngine().allocate(
            signal=self.signal(),
            runtime_snapshot=RUNTIME,
            portfolio_snapshot={
                "gross_exposure": "0",
                "symbol_exposure": {},
            },
        )
        self.assertEqual(result.approved_notional, Decimal("8.00"))
        self.assertFalse(result.blocked)

    def test_hold_signal_is_blocked(self):
        result = CapitalAllocationEngine().allocate(
            signal=self.signal("hold"),
            runtime_snapshot=RUNTIME,
            portfolio_snapshot={
                "gross_exposure": "0",
                "symbol_exposure": {},
            },
        )
        self.assertTrue(result.blocked)
        self.assertEqual(result.approved_notional, Decimal("0"))

    def test_portfolio_preview_never_modifies_actual(self):
        from runtime_core.models import OrderCandidate
        candidate = OrderCandidate(
            candidate_id="x",
            strategy_id="fixture",
            symbol="AAPL",
            side="buy",
            order_type="market",
            time_in_force="day",
            notional=Decimal("8"),
            reference_price=Decimal("200"),
            broker_mode="paper",
            submit_allowed=False,
        )
        original = {
            "gross_exposure": "0",
            "symbol_exposure": {},
        }
        result = PortfolioExposureManager().preview_apply(
            candidate=candidate,
            portfolio_snapshot=original,
        )
        self.assertEqual(original["gross_exposure"], "0")
        self.assertFalse(result["actual_portfolio_modified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
