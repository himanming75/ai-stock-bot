from pathlib import Path
import unittest

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=Path("dashboard/operations_dashboard_v3_1.py").read_text(encoding="utf-8")

    def test_read_only_endpoints(self):
        self.assertIn('p=="/api/status"',self.t)
        self.assertNotIn("do_POST",self.t)
        self.assertNotIn("do_PUT",self.t)
        self.assertNotIn("do_DELETE",self.t)

    def test_reuses_runtime_reports(self):
        for x in (
            "latest_runtime_observation_gate_v2_9_4.json",
            "latest_validation_report.json",
            "shadow_candidate_ledger.jsonl",
            "session_ledger.jsonl",
        ):
            self.assertIn(x,self.t)

    def test_no_broker_order_code(self):
        for x in ("TradingClient(","submit_order(","MarketOrderRequest(","place_order("):
            self.assertNotIn(x,self.t)

    def test_localhost_default(self):
        self.assertIn('default="127.0.0.1"',self.t)
        self.assertIn("default=8765",self.t)

    def test_safety_contract(self):
        self.assertIn('"read_only":True',self.t)
        self.assertIn('"production_parameter_modified":False',self.t)

if __name__=="__main__":
    unittest.main()
