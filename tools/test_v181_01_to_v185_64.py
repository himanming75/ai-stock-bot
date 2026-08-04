import tempfile,unittest
from pathlib import Path
from portfolio_broker.adapters import FixtureBrokerAdapter
from portfolio_broker.portfolio import aggregate
from portfolio_broker.risk import evaluate as risk
from portfolio_broker.engine import evaluate

FIX={"account":{"account_id_masked":"****1","mode":"PAPER","status":"ACTIVE","cash":500,"equity":1000,"buying_power":500},"positions":[{"symbol":"AAPL","quantity":1,"market_value":100,"average_price":95,"current_price":100,"strategy_id":"momentum"}],"orders":[]}

class Tests(unittest.TestCase):
    def test_adapter_read_only(self):
        a=FixtureBrokerAdapter("ALPACA_PAPER",FIX)
        self.assertTrue(a.read_only)
        self.assertFalse(a.supports_orders)
    def test_submit_blocked(self):
        a=FixtureBrokerAdapter("X",FIX)
        self.assertEqual(a.submit_order({})["error"],"BROKER_WRITE_DISABLED")
    def test_aggregate(self):
        p=aggregate([FixtureBrokerAdapter("X",FIX)])
        self.assertEqual(p["summary"]["total_equity"],1000)
    def test_risk(self):
        p=aggregate([FixtureBrokerAdapter("X",FIX)])
        policy={"maximum_accounts":5,"maximum_positions":10,"maximum_gross_exposure_pct":50,"maximum_symbol_weight_pct":20,"minimum_cash_weight_pct":10,"broker_write_enabled":False,"live_submission_enabled":False}
        self.assertTrue(risk(p,policy)["passed"])
    def test_empty_engine_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["actual_live_orders_submitted"],0)
    def test_empty_engine_ready(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(evaluate(Path(t))["broker_adapter_foundation_ready"])

if __name__=="__main__":unittest.main()
