import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "order_execution_simulator_v40_0.py"
)
SPEC = importlib.util.spec_from_file_location(
    "order_execution_simulator_v40_0",
    MODULE_PATH,
)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


class OrderExecutionSimulatorV400Tests(unittest.TestCase):
    def account(self, **overrides):
        data = {
            "cash": "50000",
            "equity": "100000",
            "gross_exposure": "30000",
            "symbol_exposure": "10000",
            "daily_realized_pnl": "-500",
        }
        data.update(overrides)
        return MOD.AccountState(**data)

    def request(self, **overrides):
        data = {
            "symbol": "AAPL",
            "side": "buy",
            "quantity": "10",
            "price": "200",
            "first_fill_quantity": "4",
            "second_fill_quantity": "6",
            "second_fill_price": "210",
        }
        data.update(overrides)
        return MOD.ExecutionRequest(**data)

    def test_full_fill(self):
        sim = MOD.OrderExecutionSimulator(account=self.account())
        receipt = sim.execute(self.request())
        self.assertEqual(receipt.status, "filled")
        self.assertEqual(receipt.filled_quantity, "10")
        self.assertEqual(receipt.remaining_quantity, "0")
        self.assertEqual(receipt.average_fill_price, "206")

    def test_partial_fill(self):
        sim = MOD.OrderExecutionSimulator(account=self.account())
        receipt = sim.execute(
            self.request(
                second_fill_quantity=None,
                second_fill_price=None,
            )
        )
        self.assertEqual(receipt.status, "partially_filled")
        self.assertEqual(receipt.filled_quantity, "4")
        self.assertEqual(receipt.remaining_quantity, "6")

    def test_risk_rejection(self):
        sim = MOD.OrderExecutionSimulator(account=self.account())
        receipt = sim.execute(
            self.request(
                quantity="200",
                first_fill_quantity="200",
                second_fill_quantity=None,
                second_fill_price=None,
            )
        )
        self.assertEqual(receipt.status, "rejected_risk")
        self.assertEqual(receipt.filled_quantity, "0")
        self.assertTrue(receipt.rejection_reasons)

    def test_insufficient_cash_rejection(self):
        sim = MOD.OrderExecutionSimulator(
            account=self.account(cash="100")
        )
        receipt = sim.execute(self.request())
        self.assertEqual(receipt.status, "rejected_risk")
        self.assertIn(
            "Available cash is insufficient for the order.",
            receipt.rejection_reasons,
        )

    def test_daily_loss_rejection(self):
        sim = MOD.OrderExecutionSimulator(
            account=self.account(daily_realized_pnl="-2000")
        )
        receipt = sim.execute(self.request())
        self.assertEqual(receipt.status, "rejected_risk")

    def test_portfolio_cash_after_buy(self):
        sim = MOD.OrderExecutionSimulator(account=self.account())
        receipt = sim.execute(self.request())
        self.assertEqual(receipt.portfolio_cash, "47940")

    def test_portfolio_market_value_after_buy(self):
        sim = MOD.OrderExecutionSimulator(account=self.account())
        receipt = sim.execute(self.request())
        self.assertEqual(receipt.portfolio_market_value, "32060")

    def test_portfolio_equity_preserved(self):
        sim = MOD.OrderExecutionSimulator(account=self.account())
        receipt = sim.execute(self.request())
        self.assertEqual(receipt.portfolio_equity, "80000")

    def test_event_hashes_present(self):
        sim = MOD.OrderExecutionSimulator(account=self.account())
        sim.execute(self.request())
        self.assertTrue(
            all(
                len(event.event_sha256) == 64
                for event in sim.audit_log()
            )
        )

    def test_receipt_hash_present(self):
        sim = MOD.OrderExecutionSimulator(account=self.account())
        receipt = sim.execute(self.request())
        self.assertEqual(len(receipt.receipt_sha256), 64)

    def test_no_network_usage(self):
        sim = MOD.OrderExecutionSimulator(account=self.account())
        receipt = sim.execute(self.request())
        self.assertFalse(receipt.network_used)
        self.assertFalse(sim.export(receipt)["network_used"])

    def test_overfill_input_rejected(self):
        sim = MOD.OrderExecutionSimulator(account=self.account())
        with self.assertRaises(ValueError):
            sim.execute(
                self.request(
                    quantity="10",
                    first_fill_quantity="8",
                    second_fill_quantity="5",
                )
            )

    def test_sell_exposure_rejection(self):
        sim = MOD.OrderExecutionSimulator(account=self.account())
        receipt = sim.execute(
            self.request(
                side="sell",
                quantity="100",
                price="200",
                first_fill_quantity="100",
                second_fill_quantity=None,
                second_fill_price=None,
            )
        )
        self.assertEqual(receipt.status, "rejected_risk")

    def test_audit_stages_full_fill(self):
        sim = MOD.OrderExecutionSimulator(account=self.account())
        sim.execute(self.request())
        stages = [event.stage for event in sim.audit_log()]
        self.assertIn("risk_check", stages)
        self.assertIn("order_accepted", stages)
        self.assertIn("position_update", stages)
        self.assertIn("portfolio_update", stages)


if __name__ == "__main__":
    unittest.main(verbosity=2)
