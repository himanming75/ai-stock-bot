import tempfile, unittest
from pathlib import Path
from paper_broker_read_model.models import (
    normalize_account,
    normalize_positions,
    internal_account_from_ledger,
)
from paper_broker_read_model.reconciliation import (
    compare_value,
    reconcile_account,
    reconcile_positions,
)
from paper_broker_read_model.freshness import evaluate_snapshot_freshness
from paper_broker_read_model.integrity import evaluate_integrity
from paper_broker_read_model.engine import evaluate

class Tests(unittest.TestCase):
    def test_normalize_account(self):
        self.assertEqual(normalize_account({"equity":"10"})["equity"],10.0)

    def test_normalize_positions(self):
        rows=normalize_positions([{"symbol":"aapl","quantity":"5"}])
        self.assertIn("AAPL",rows)

    def test_internal_account(self):
        value=internal_account_from_ledger({
            "cash_reconciliation":{"reported_ending_cash":100},
            "equity_reconciliation":{"reported_equity":110},
        })
        self.assertEqual(value["buying_power"],100)

    def test_compare_value(self):
        self.assertTrue(compare_value(100,100,.01)["passed"])

    def test_account_reconciliation(self):
        broker={"cash":100,"equity":110,"buying_power":100,"currency":"USD","status":"ACTIVE"}
        self.assertTrue(reconcile_account(broker,dict(broker),{})["passed"])

    def test_position_reconciliation(self):
        row={"AAPL":{"quantity":5,"average_cost":100,"market_value":500}}
        self.assertTrue(reconcile_positions(row,row,{})["passed"])

    def test_freshness_invalid(self):
        self.assertFalse(
            evaluate_snapshot_freshness("",100)["passed"]
        )

    def test_integrity(self):
        adapter={
            "safe_api_boundary":{"passed":True},
            "read_only_adapter":True,
            "actual_credentials_used":False,
            "actual_external_network_used":False,
            "actual_orders_submitted":0,
        }
        result=evaluate_integrity(
            {"passed":True},
            {"passed":True},
            {"passed":True},
            adapter,
        )
        self.assertTrue(result["passed"])

    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(
                evaluate(Path(t))["state"],
                "PAPER_BROKER_READ_MODEL_SOURCE_REQUIRED",
            )

    def test_safety(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(evaluate(Path(t))["order_submission_enabled"])

if __name__=="__main__":
    unittest.main()
