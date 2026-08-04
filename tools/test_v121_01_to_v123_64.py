import tempfile,unittest
from pathlib import Path
from alpaca_paper_operations.config import credential_status
from alpaca_paper_operations.mock import MockAlpacaPaperClient
from alpaca_paper_operations.normalize import normalize_account,normalize_positions
from alpaca_paper_operations.order_gate import validate_order,submission_gate
from alpaca_paper_operations.qualification import evaluate_qualification
from alpaca_paper_operations.engine import evaluate

POLICY={
"allowed_symbols":["AAPL"],"maximum_quantity":10,"paper_mode":True,
"live_base_url_prohibited":True,"paper_submission_enabled":True,
"live_submission_enabled":False,
}
class Tests(unittest.TestCase):
    def test_credentials_hidden(self):
        self.assertFalse(credential_status()["values_exposed"])
    def test_mock(self):
        c=MockAlpacaPaperClient({"account":{"equity":"100"}})
        self.assertEqual(c.account().status_code,200)
    def test_normalize(self):
        self.assertEqual(normalize_account({"equity":"100"})["equity"],100)
        p=normalize_positions([{"symbol":"aapl","qty":"2"}])
        self.assertEqual(p[0]["symbol"],"AAPL")
    def test_validation(self):
        v=validate_order({
            "symbol":"AAPL","qty":"1","side":"buy",
            "type":"market","time_in_force":"day",
        },POLICY)
        self.assertTrue(v["passed"])
    def test_gate_blocked_without_explicit(self):
        v={"passed":True}
        self.assertFalse(submission_gate(v,POLICY,False,True)["authorized"])
    def test_qualification_requires_sessions(self):
        q=evaluate_qualification([],{"minimum_qualification_sessions":20})
        self.assertFalse(q["passed"])
    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["state"],
                "ALPACA_PAPER_OPERATIONS_SOURCE_REQUIRED")
    def test_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["actual_orders_submitted"],0)

if __name__=="__main__":unittest.main()
