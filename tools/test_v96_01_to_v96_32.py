import tempfile, unittest
from pathlib import Path
from paper_account_ledger.ledger import (
    build_cash_entries, build_position_entries, aggregate_positions
)
from paper_account_ledger.reconciliation import (
    find_duplicate_fill_ids, reconcile_cash,
    reconcile_positions, reconcile_equity
)
from paper_account_ledger.integrity import evaluate_integrity
from paper_account_ledger.engine import evaluate

class Tests(unittest.TestCase):
    def test_cash_entries(self):
        simulation={"initial_cash":1000,"fills":[{"cash_effect":-100,"fill_id":"f1"}]}
        self.assertEqual(sum(x["amount"] for x in build_cash_entries(simulation,{})),900)
    def test_position_entries(self):
        simulation={"fills":[{"state":"FILLED","filled_quantity":5,"side":"BUY","symbol":"AAPL","fill_id":"f1"}]}
        self.assertEqual(build_position_entries(simulation,{})[0]["quantity_delta"],5)
    def test_aggregate_positions(self):
        rows=[{"symbol":"AAPL","quantity_delta":5},{"symbol":"AAPL","quantity_delta":-2}]
        self.assertEqual(aggregate_positions(rows)["AAPL"],3)
    def test_duplicate_fills(self):
        fills=[{"fill_id":"a"},{"fill_id":"a"}]
        self.assertEqual(find_duplicate_fill_ids(fills),["a"])
    def test_cash_reconciliation(self):
        self.assertTrue(reconcile_cash([{"amount":100}],100,.01)["passed"])
    def test_position_reconciliation(self):
        self.assertTrue(reconcile_positions({"AAPL":5},{"AAPL":{"quantity":5}},.001)["passed"])
    def test_equity_reconciliation(self):
        self.assertTrue(reconcile_equity(100,50,150,.01)["passed"])
    def test_integrity(self):
        result=evaluate_integrity([],{"passed":True},{"passed":True},{"passed":True},0,0)
        self.assertTrue(result["passed"])
    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(
                evaluate(Path(t))["state"],
                "PAPER_ACCOUNT_LEDGER_SOURCE_REQUIRED",
            )
    def test_safety(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(evaluate(Path(t))["order_submission_enabled"])

if __name__=="__main__":
    unittest.main()
