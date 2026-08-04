import tempfile,unittest
from pathlib import Path
from dynamic_live_risk.sizing import calculate
from dynamic_live_risk.budget import allocate
from dynamic_live_risk.exposure import evaluate as exposure
from dynamic_live_risk.loss_limits import evaluate as losses
from dynamic_live_risk.concentration import evaluate as concentration
from dynamic_live_risk.certificate import build
from dynamic_live_risk.engine import evaluate

POLICY={
"risk_per_trade_pct":0.5,"target_volatility_pct":1.5,
"default_stop_distance_pct":2,"default_volatility_pct":1.5,
"maximum_quantity":1,"maximum_order_notional":250,
"default_strategy_risk_budget_pct":1,"default_symbol_risk_budget_pct":1,
"maximum_gross_exposure_pct":25,"minimum_cash_pct":50,
"maximum_daily_loss_pct":1,"maximum_weekly_loss_pct":3,
"current_daily_pnl":0,"current_weekly_pnl":0,
"current_consecutive_losses":0,"maximum_consecutive_losses":3,
"maximum_positions_per_sector":2,"current_correlation_cluster_count":0,
"maximum_correlation_cluster_count":2,"sector_map":{"AAPL":"TECH"},
"live_network_enabled":False,"live_submission_enabled":False,
}
C={"symbol":"AAPL","reference_price":200,"stop_distance_pct":2,
"volatility_pct":1.5,"source_strategy_id":"S"}
A={"equity":1000,"cash":1000}

class Tests(unittest.TestCase):
    def test_sizing(self):
        self.assertEqual(calculate(C,A,POLICY)["final_quantity"],1)
    def test_budget(self):
        s=calculate(C,A,POLICY)
        self.assertTrue(allocate(C,s,POLICY)["budget_passed"])
    def test_exposure(self):
        self.assertTrue(exposure(A,[],calculate(C,A,POLICY),POLICY)["passed"])
    def test_losses(self):
        self.assertTrue(losses(A,POLICY)["passed"])
    def test_concentration(self):
        self.assertTrue(concentration(C,[],POLICY)["passed"])
    def test_certificate(self):
        self.assertEqual(len(build(True,{"x":1})["certificate_sha256"]),64)
    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["state"],"DYNAMIC_LIVE_RISK_SOURCE_REQUIRED")
    def test_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["actual_live_orders_submitted"],0)

if __name__=="__main__":unittest.main()
