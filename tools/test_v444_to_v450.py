
from __future__ import annotations
import unittest
from ai_risk_allocation.sector_exposure import apply_sector_exposure_limits
from ai_risk_allocation.portfolio_risk_budget import apply_portfolio_risk_budget
from ai_risk_allocation.drawdown_scaling import drawdown_multiplier, apply_drawdown_scaling
from ai_risk_allocation.correlation_adjustment import apply_correlation_adjustment
from ai_risk_allocation.cash_reserve import apply_dynamic_cash_reserve
from ai_risk_allocation.integrated_allocation import build_integrated_allocation
from ai_risk_allocation.allocation_qualification import qualify_allocation

def payload():
    return {
        "account_equity": 100000, "risk_per_trade_pct": 0.01,
        "maximum_position_pct": 0.25, "allow_fractional_shares": True,
        "minimum_notional": 1, "kelly_fraction": 0.5, "maximum_kelly_pct": 0.2,
        "target_volatility": 0.2, "minimum_volatility_multiplier": 0.25,
        "maximum_volatility_multiplier": 1.0,
        "default_sector_limit_pct": 0.30, "sector_limits": {"TECH": 0.25, "HEALTH": 0.20},
        "maximum_portfolio_risk_pct": 0.03, "current_drawdown_pct": 0.04,
        "drawdown_tiers": [{"max_drawdown_pct":0.03,"multiplier":1.0},{"max_drawdown_pct":0.06,"multiplier":0.75},{"max_drawdown_pct":0.10,"multiplier":0.5}],
        "correlation_threshold": 0.75, "high_correlation_multiplier": 0.7,
        "minimum_cash_reserve_pct": 0.10, "maximum_cash_reserve_pct": 0.50,
        "market_volatility": 0.35, "high_volatility_threshold": 0.30,
        "high_volatility_cash_add_pct": 0.10, "cash_drawdown_threshold": 0.05,
        "drawdown_cash_add_pct": 0.10,
        "positions": [
            {"symbol":"NVDA","sector":"TECH","reference_price":180.5,"stop_loss_pct":0.05,"proposed_weight":0.23},
            {"symbol":"MSFT","sector":"TECH","reference_price":525.25,"stop_loss_pct":0.04,"proposed_weight":0.22},
            {"symbol":"JNJ","sector":"HEALTH","reference_price":168.4,"stop_loss_pct":0.03,"proposed_weight":0.18},
        ],
        "kelly_statistics": [
            {"symbol":"NVDA","win_rate":0.58,"average_win":0.10,"average_loss":0.05},
            {"symbol":"MSFT","win_rate":0.62,"average_win":0.07,"average_loss":0.035},
            {"symbol":"JNJ","win_rate":0.55,"average_win":0.045,"average_loss":0.03},
        ],
        "volatility_statistics": [
            {"symbol":"NVDA","annualized_volatility":0.55},
            {"symbol":"MSFT","annualized_volatility":0.28},
            {"symbol":"JNJ","annualized_volatility":0.18},
        ],
        "correlation_pairs": [
            {"symbol_a":"NVDA","symbol_b":"MSFT","correlation":0.86},
            {"symbol_a":"NVDA","symbol_b":"JNJ","correlation":0.20},
            {"symbol_a":"MSFT","symbol_b":"JNJ","correlation":0.15},
        ],
    }

class Tests(unittest.TestCase):
    def test_sector_limit(self):
        r = apply_sector_exposure_limits(payload())
        self.assertLessEqual(r["sector_exposure"]["TECH"], 25000.01)
    def test_risk_budget(self):
        r = apply_portfolio_risk_budget(payload())
        self.assertLessEqual(r["total_risk_at_stop"], 3000.01)
    def test_drawdown_multiplier(self):
        self.assertEqual(drawdown_multiplier(0.04, payload()["drawdown_tiers"]), 0.75)
    def test_drawdown_scaling(self):
        r = apply_drawdown_scaling(payload())
        self.assertEqual(r["drawdown_multiplier"], 0.75)
    def test_correlation_adjustment(self):
        r = apply_correlation_adjustment(payload())
        msft = [x for x in r["positions"] if x["symbol"]=="MSFT"][0]
        self.assertEqual(msft["correlation_multiplier"], 0.7)
    def test_cash_reserve(self):
        r = apply_dynamic_cash_reserve(payload())
        self.assertGreaterEqual(r["remaining_cash"] + 0.01, r["required_cash_reserve_amount"])
    def test_integrated_hash(self):
        self.assertEqual(len(build_integrated_allocation(payload())["allocation_hash"]), 64)
    def test_qualification(self):
        self.assertTrue(qualify_allocation(payload())["qualified"])
    def test_zero_orders(self):
        r = qualify_allocation(payload())
        self.assertEqual(r["actual_paper_orders_submitted"], 0)
        self.assertEqual(r["actual_live_orders_submitted"], 0)
        self.assertFalse(r["order_submission_allowed"])
    def test_deterministic_allocation_values(self):
        a = build_integrated_allocation(payload())
        b = build_integrated_allocation(payload())
        self.assertEqual(a["total_recommended_notional"], b["total_recommended_notional"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
