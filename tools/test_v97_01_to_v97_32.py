import tempfile, unittest
from pathlib import Path
from paper_broker_adapter.mock import MockPaperBrokerAdapter
from paper_broker_adapter.alpaca_readonly import AlpacaReadOnlyAdapter
from paper_broker_adapter.ibkr_readonly import IBKRReadOnlyAdapter
from paper_broker_adapter.factory import create_adapter
from paper_broker_adapter.translators import (
    translate_account, translate_position, translate_order_plan
)
from paper_broker_adapter.boundary import (
    validate_safe_boundary, block_write
)
from paper_broker_adapter.engine import evaluate

class Tests(unittest.TestCase):
    def test_mock_capabilities(self):
        adapter=MockPaperBrokerAdapter()
        self.assertFalse(adapter.capabilities()["order_submit"])

    def test_mock_snapshot(self):
        adapter=MockPaperBrokerAdapter(
            account={"cash":1,"equity":2,"buying_power":1}
        )
        self.assertEqual(adapter.get_account_snapshot()["equity"],2)

    def test_alpaca_read_only(self):
        adapter=AlpacaReadOnlyAdapter()
        self.assertTrue(adapter.capabilities()["read_only"])
        self.assertFalse(adapter.health_check()["network_used"])

    def test_ibkr_read_only(self):
        adapter=IBKRReadOnlyAdapter()
        self.assertFalse(adapter.capabilities()["order_cancel"])

    def test_factory(self):
        self.assertEqual(create_adapter("MOCK").name,"MOCK_PAPER")

    def test_translators(self):
        self.assertEqual(
            translate_account({"equity":"10"})["equity"],10.0
        )
        self.assertEqual(
            translate_position({"symbol":"AAPL"})["symbol"],"AAPL"
        )
        self.assertFalse(
            translate_order_plan({"symbol":"AAPL"})["submission_allowed"]
        )

    def test_boundary(self):
        caps=MockPaperBrokerAdapter().capabilities()
        self.assertTrue(validate_safe_boundary(caps)["passed"])

    def test_write_blocked(self):
        with self.assertRaises(PermissionError):
            block_write("submit_order")

    def test_adapter_submit_blocked(self):
        with self.assertRaises(PermissionError):
            MockPaperBrokerAdapter().submit_order({})

    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(
                evaluate(Path(t))["state"],
                "PAPER_BROKER_ADAPTER_SOURCE_REQUIRED",
            )

    def test_safety(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(evaluate(Path(t))["order_submission_enabled"])

if __name__=="__main__":
    unittest.main()
