
from pathlib import Path
import importlib.util
import unittest

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load(Path("dashboard/strategy_weakness_map_v3_17.py"), "v317")
        cls.analytics = Path("dashboard/trade_analytics_v3_5.py").read_text(encoding="utf-8")
        cls.html = Path("dashboard/templates/operations_dashboard_v3_2.html").read_text(encoding="utf-8")

    def base_payload(self):
        return {
            "historical": {
                "numeric_trade_count": 2,
                "net_realized_pnl": 1.0,
                "profit_factor": "INF",
                "average_trade": 0.5,
                "max_realized_drawdown": 0,
            },
            "performance_diagnostics": {
                "minimum_sample_required": 10,
                "canonical_numeric_trade_count": 2,
                "loss_count": 0,
                "by_symbol": [{"name": "AAPL", "numeric_trade_count": 2}],
            },
            "strategy_readiness": {
                "status": "NOT_READY",
                "overall_score": 49,
                "blockers": ["sample"],
            },
            "strategy_stress_test": {
                "sample_status": "INSUFFICIENT_SAMPLE",
                "canonical_numeric_trade_count": 2,
                "minimum_interpretation_sample": 10,
                "scenarios": [{}, {}, {}, {}],
            },
            "strategy_robustness": {
                "sample_status": "INSUFFICIENT_SAMPLE",
                "robustness_score": 49,
                "raw_robustness_score": 80,
                "canonical_numeric_trade_count": 2,
            },
            "market_regime_analysis": {
                "status": "PASS_NO_EXPLICIT_REGIME_EVIDENCE",
                "evidence_trade_count": 0,
                "coverage": {
                    "direction_coverage": 0,
                    "volatility_coverage": 0,
                },
            },
        }

    def test_sample_is_evidence_gap_not_performance_failure(self):
        result = self.m.build_strategy_weakness_map(self.base_payload())
        sample = [x for x in result["issues"] if x["code"] == "SAMPLE_SIZE_INSUFFICIENT"][0]
        self.assertEqual(sample["weakness_type"], "EVIDENCE_GAP")
        self.assertEqual(sample["severity"], "CRITICAL")

    def test_no_losses_marked_unobserved(self):
        result = self.m.build_strategy_weakness_map(self.base_payload())
        codes = [x["code"] for x in result["issues"]]
        self.assertIn("NO_LOSING_TRADES_OBSERVED", codes)

    def test_no_profitability_failure_from_two_winners(self):
        result = self.m.build_strategy_weakness_map(self.base_payload())
        codes = [x["code"] for x in result["issues"]]
        self.assertNotIn("PROFIT_FACTOR_THIN", codes)
        self.assertNotIn("NET_PNL_NON_POSITIVE", codes)

    def test_api_exposed(self):
        self.assertIn('"strategy_weakness_map": weakness_map', self.analytics)

    def test_ui_and_safety(self):
        self.assertIn('id="weaknessMapSection"', self.html)
        self.assertIn("Strategy Weakness Map / 전략 약점 지도", self.html)
        combined = (
            Path("dashboard/strategy_weakness_map_v3_17.py").read_text(encoding="utf-8")
            + self.analytics
            + self.html
        )
        for bad in ("TradingClient(", "submit_order(", "MarketOrderRequest("):
            self.assertNotIn(bad, combined)

if __name__ == "__main__":
    unittest.main()
