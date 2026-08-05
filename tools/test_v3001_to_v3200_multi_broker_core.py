from __future__ import annotations
import inspect, tempfile, unittest
from decimal import Decimal
from pathlib import Path
from multi_broker_core.factory import BrokerFactory
from multi_broker_core.models import OrderRequest
from multi_broker_core.registry import default_registry
from multi_broker_core.symbols import normalize_equity_symbol
from multi_broker_core.certification import certify


class Tests(unittest.TestCase):
    def test_factory_mock(self):
        self.assertEqual(BrokerFactory().create("mock").broker_name, "MOCK")

    def test_registry(self):
        brokers = [x.broker for x in default_registry().list_all()]
        self.assertEqual(brokers, ["ALPACA", "ETRADE", "IBKR", "MOCK"])

    def test_symbol_normalization(self):
        self.assertEqual(normalize_equity_symbol(" brk/b "), "BRK.B")

    def test_order_validation(self):
        request = OrderRequest(
            symbol="SPY", side="BUY", quantity=Decimal("1"),
            order_type="LIMIT", time_in_force="DAY", limit_price=Decimal("500")
        )
        request.validate()

    def test_submission_blocked(self):
        adapter = BrokerFactory().create("MOCK")
        with self.assertRaises(PermissionError):
            adapter.submit_order(OrderRequest(
                symbol="SPY", side="BUY", quantity=Decimal("1"),
                order_type="MARKET", time_in_force="DAY"
            ))

    def test_certification_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            result = certify(Path(d))
            self.assertEqual(result["status"], "PASS")
            self.assertTrue((Path(d) / "multi_broker_core_ledger.jsonl").exists())

    def test_zero_order_contract(self):
        source = inspect.getsource(certify)
        self.assertIn('"actual_broker_write_performed": False', source)
        self.assertIn('"actual_paper_orders_submitted": 0', source)
        self.assertIn('"actual_live_orders_submitted": 0', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
