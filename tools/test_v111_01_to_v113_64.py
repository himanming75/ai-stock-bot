import tempfile,unittest
from pathlib import Path

from live_broker_readonly.capabilities import (
    get_capabilities,validate_read_only
)
from live_broker_readonly.credentials import inspect_credential_presence
from live_broker_readonly.adapters import build_adapter
from live_broker_readonly.normalize import (
    normalize_account,normalize_positions,normalize_orders
)
from live_broker_readonly.reconcile import compare_number,reconcile
from live_broker_readonly.drift import detect_drift
from live_broker_readonly.boundary import evaluate_boundary
from live_broker_readonly.engine import evaluate

class Tests(unittest.TestCase):
    def test_capabilities(self):
        value=get_capabilities("ALPACA_READ_ONLY")
        self.assertTrue(value["read_only"])
        self.assertFalse(value["order_submit"])

    def test_validate_read_only(self):
        self.assertTrue(validate_read_only(
            get_capabilities("IBKR_READ_ONLY")
        )["passed"])

    def test_credentials_not_exposed(self):
        value=inspect_credential_presence("ETRADE_READ_ONLY")
        self.assertFalse(value["values_exposed"])
        self.assertFalse(value["credentials_used"])

    def test_write_blocked(self):
        adapter=build_adapter("MOCK_READ_ONLY",{})
        with self.assertRaises(PermissionError):
            adapter.submit_order({})

    def test_normalize(self):
        account=normalize_account({"equity":"100.12"})
        self.assertEqual(account["equity"],100.12)
        positions=normalize_positions([{
            "symbol":"aapl","quantity":2,
            "average_cost":100,"market_price":110,
        }])
        self.assertEqual(positions[0]["market_value"],220)
        orders=normalize_orders([{"symbol":"aapl","status":"new"}])
        self.assertEqual(orders[0]["status"],"NEW")

    def test_compare(self):
        self.assertTrue(compare_number(100,100.5,1)["passed"])

    def test_reconcile(self):
        value=reconcile(
            {"cash":100,"equity":100},
            [],
            {"cash":100,"equity":100},
            [],
            {"money_tolerance":1,"quantity_tolerance":0.001},
        )
        self.assertTrue(value["passed"])

    def test_drift(self):
        value=detect_drift({
            "account":{"cash":{"passed":False,"difference":2}},
            "positions":{},
        },[])
        self.assertTrue(value["drift_detected"])

    def test_boundary(self):
        self.assertTrue(evaluate_boundary(
            get_capabilities("MOCK_READ_ONLY")
        )["passed"])

    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as temp:
            result=evaluate(Path(temp))
            self.assertEqual(
                result["state"],
                "LIVE_BROKER_READ_ONLY_SOURCE_REQUIRED",
            )

    def test_orders_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(
                evaluate(Path(temp))["actual_orders_submitted"],
                0,
            )

if __name__=="__main__":
    unittest.main()
