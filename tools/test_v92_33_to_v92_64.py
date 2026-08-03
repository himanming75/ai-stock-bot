import tempfile, unittest
from pathlib import Path
from enterprise_risk_center.statistics import (
    pct_returns, historical_var, expected_shortfall,
    annualized_volatility, max_drawdown, correlation,
)
from enterprise_risk_center.stress import run_stress_scenarios
from enterprise_risk_center.monte_carlo import simulate
from enterprise_risk_center.guards import (
    daily_loss_guard, concentration_guard, volatility_guard,
)
from enterprise_risk_center.engine import evaluate

class Tests(unittest.TestCase):
    def test_returns(self):
        self.assertEqual(len(pct_returns([100,101,102])),2)
    def test_var(self):
        self.assertGreaterEqual(historical_var([-.1,.02,.03]),0)
    def test_es(self):
        self.assertGreaterEqual(expected_shortfall([-.1,-.05,.02]),0)
    def test_volatility(self):
        self.assertGreaterEqual(annualized_volatility([.01,-.01,.02]),0)
    def test_drawdown(self):
        self.assertAlmostEqual(max_drawdown([100,120,90]),25.0)
    def test_correlation(self):
        self.assertAlmostEqual(correlation([1,2,3],[2,4,6]),1.0)
    def test_stress(self):
        self.assertEqual(len(run_stress_scenarios(100000,20,[])),4)
    def test_monte_carlo(self):
        self.assertEqual(simulate([.01,-.01],100000,100,5)["iterations"],100)
    def test_daily_guard(self):
        self.assertEqual(daily_loss_guard(-6,{})["state"],"STOP_REQUIRED")
    def test_concentration_guard(self):
        self.assertFalse(concentration_guard([{"weight_pct":50}],{})["passed"])
    def test_volatility_guard(self):
        self.assertTrue(volatility_guard(20,{})["passed"])
    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(
                evaluate(Path(t))["state"],
                "ENTERPRISE_RISK_SOURCE_REQUIRED",
            )
    def test_safety(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(evaluate(Path(t))["order_submission_enabled"])

if __name__=="__main__":
    unittest.main()
