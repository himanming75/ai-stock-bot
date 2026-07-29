import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "risk_engine_v38_0.py"
)
SPEC = importlib.util.spec_from_file_location(
    "risk_engine_v38_0",
    MODULE_PATH,
)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


class RiskEngineV380Tests(unittest.TestCase):
    def setUp(self):
        self.engine = MOD.RiskEngine(MOD.default_limits())

    def account(self, **overrides):
        data = {
            "equity": "100000",
            "cash": "50000",
            "gross_exposure": "30000",
            "daily_realized_pnl": "-500",
            "symbol_exposures": {"AAPL": "10000"},
        }
        data.update(overrides)
        return MOD.AccountRiskSnapshot(**data)

    def request(self, **overrides):
        data = {
            "symbol": "AAPL",
            "side": "buy",
            "quantity": "50",
            "price": "200",
        }
        data.update(overrides)
        return MOD.OrderRiskRequest(**data)

    def test_approved_order(self):
        result = self.engine.evaluate(
            self.request(),
            self.account(),
        )
        self.assertEqual(result.decision, "approve")
        self.assertFalse(result.rejection_reasons)

    def test_max_order_notional_rejection(self):
        result = self.engine.evaluate(
            self.request(quantity="200", price="200"),
            self.account(),
        )
        self.assertEqual(result.decision, "reject")
        self.assertIn(
            "Order notional exceeds the configured maximum.",
            result.rejection_reasons,
        )

    def test_symbol_exposure_rejection(self):
        result = self.engine.evaluate(
            self.request(quantity="100", price="200"),
            self.account(symbol_exposures={"AAPL": "10000"}),
        )
        self.assertEqual(result.decision, "reject")
        self.assertIn(
            "Projected symbol exposure exceeds the configured maximum.",
            result.rejection_reasons,
        )

    def test_gross_exposure_rejection(self):
        result = self.engine.evaluate(
            self.request(quantity="100", price="200"),
            self.account(gross_exposure="90000"),
        )
        self.assertEqual(result.decision, "reject")
        self.assertIn(
            "Projected gross exposure exceeds the configured maximum.",
            result.rejection_reasons,
        )

    def test_leverage_rejection(self):
        limits = MOD.RiskLimits(
            max_order_notional="100000",
            max_symbol_exposure_pct="200",
            max_gross_exposure_pct="300",
            max_leverage="1",
            max_daily_loss="2000",
            max_position_quantity="10000",
        )
        engine = MOD.RiskEngine(limits)
        result = engine.evaluate(
            self.request(quantity="400", price="200"),
            self.account(gross_exposure="50000", cash="100000"),
        )
        self.assertEqual(result.decision, "reject")
        self.assertIn(
            "Projected leverage exceeds the configured maximum.",
            result.rejection_reasons,
        )

    def test_daily_loss_limit_rejection(self):
        result = self.engine.evaluate(
            self.request(),
            self.account(daily_realized_pnl="-2000"),
        )
        self.assertEqual(result.decision, "reject")
        self.assertIn(
            "Daily realized loss limit has been reached or exceeded.",
            result.rejection_reasons,
        )

    def test_insufficient_cash_rejection(self):
        result = self.engine.evaluate(
            self.request(quantity="50", price="200"),
            self.account(cash="5000"),
        )
        self.assertEqual(result.decision, "reject")
        self.assertIn(
            "Available cash is insufficient for the order.",
            result.rejection_reasons,
        )

    def test_sell_exposure_rejection(self):
        result = self.engine.evaluate(
            self.request(side="sell", quantity="100", price="200"),
            self.account(symbol_exposures={"AAPL": "10000"}),
        )
        self.assertEqual(result.decision, "reject")
        self.assertIn(
            "Sell order exceeds the current symbol exposure.",
            result.rejection_reasons,
        )

    def test_position_quantity_rejection(self):
        result = self.engine.evaluate(
            self.request(quantity="1001", price="1"),
            self.account(),
        )
        self.assertEqual(result.decision, "reject")
        self.assertIn(
            "Order quantity exceeds the configured maximum.",
            result.rejection_reasons,
        )

    def test_decision_hash_present(self):
        result = self.engine.evaluate(
            self.request(),
            self.account(),
        )
        self.assertEqual(len(result.decision_sha256), 64)

    def test_ledger_records_decisions(self):
        self.engine.evaluate(self.request(), self.account())
        self.engine.evaluate(
            self.request(quantity="1000"),
            self.account(),
        )
        self.assertEqual(len(self.engine.ledger()), 2)
        self.assertEqual(
            self.engine.export()["decision_count"],
            2,
        )

    def test_no_network_usage(self):
        result = self.engine.evaluate(
            self.request(),
            self.account(),
        )
        self.assertFalse(result.network_used)
        self.assertFalse(self.engine.export()["network_used"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
