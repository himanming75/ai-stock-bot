from __future__ import annotations

import unittest

from backtest_v2.models import Bar
from multi_asset_backtest.benchmark import buy_and_hold
from multi_asset_backtest.correlation import correlation_matrix, pearson
from multi_asset_backtest.engine import run_multi_asset_backtest
from multi_asset_backtest.portfolio import concentration_metrics


def make_bars(start: float, drift: float, count: int = 180):
    rows = []
    close = start
    for i in range(count):
        cycle = 0.4 if i % 30 < 18 else -0.25
        close += drift + cycle
        rows.append({
            "timestamp": f"2026-{(i//28)%12+1:02d}-{(i%28)+1:02d}",
            "open": close - 0.2,
            "high": close + 0.6,
            "low": close - 0.6,
            "close": close,
            "volume": 100000 + i * 100,
        })
    return rows


def sample_assets():
    return [
        {"symbol": "AAPL", "sector": "TECH", "weight": 0.4, "bars": make_bars(100, 0.12)},
        {"symbol": "JNJ", "sector": "HEALTH", "weight": 0.3, "bars": make_bars(80, 0.08)},
        {"symbol": "XOM", "sector": "ENERGY", "weight": 0.3, "bars": make_bars(60, 0.10)},
    ]


def policy():
    return {
        "total_initial_cash": 100000,
        "minimum_asset_count": 3,
        "maximum_asset_weight_pct": 50,
        "minimum_effective_asset_count": 2,
        "backtest_policy": {
            "fast_period": 5,
            "slow_period": 15,
            "position_fraction": 0.9,
            "commission_bps": 1,
            "slippage_bps": 2,
        },
    }


class MultiAssetBacktestTests(unittest.TestCase):
    def test_buy_and_hold(self):
        bars = [Bar.from_dict(row) for row in make_bars(100, 0.1, 20)]
        result = buy_and_hold(bars, 10000)
        self.assertGreater(result["ending_equity"], 0)

    def test_pearson_identity(self):
        self.assertAlmostEqual(pearson([1, 2, 3], [1, 2, 3]), 1.0)

    def test_correlation_matrix(self):
        matrix = correlation_matrix({
            "A": [1, 2, 3, 4],
            "B": [2, 3, 4, 5],
        })
        self.assertEqual(matrix["A"]["A"], 1.0)

    def test_concentration(self):
        result = concentration_metrics({"A": 0.5, "B": 0.5})
        self.assertEqual(result["largest_weight_pct"], 50.0)
        self.assertEqual(result["effective_asset_count"], 2.0)

    def test_multi_asset_runs(self):
        result = run_multi_asset_backtest(sample_assets(), policy())
        self.assertEqual(result["asset_count"], 3)
        self.assertEqual(len(result["per_asset"]), 3)

    def test_benchmark_available(self):
        result = run_multi_asset_backtest(sample_assets(), policy())
        self.assertGreater(result["benchmark"]["ending_equity"], 0)

    def test_certificate_hash(self):
        result = run_multi_asset_backtest(sample_assets(), policy())
        self.assertEqual(len(result["certificate"]["certificate_sha256"]), 64)

    def test_safety_defaults(self):
        result = run_multi_asset_backtest(sample_assets(), policy())
        self.assertTrue(result["paper_only"])
        self.assertFalse(result["broker_write_enabled"])
        self.assertFalse(result["order_submission_enabled"])


if __name__ == "__main__":
    unittest.main()
