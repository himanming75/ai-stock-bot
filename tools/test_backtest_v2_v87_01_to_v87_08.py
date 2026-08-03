from __future__ import annotations

import unittest

from backtest_v2.broker import (
    apply_buy_fill,
    apply_sell_fill,
    commission_for,
)
from backtest_v2.engine import run_backtest
from backtest_v2.models import Bar
from backtest_v2.statistics import (
    max_drawdown,
    trade_statistics,
)
from backtest_v2.strategy import crossover_signal


def sample_bars(count=180):
    bars = []
    close = 100.0
    for index in range(count):
        cycle = index % 40
        if cycle < 20:
            close += 0.8
        else:
            close -= 0.6
        bars.append(Bar(
            timestamp=f"2026-01-{(index % 28)+1:02d}T16:00:00Z",
            open=close - 0.2,
            high=close + 0.6,
            low=close - 0.6,
            close=close,
            volume=100000 + index * 100,
        ))
    return bars


class BacktestV2Tests(unittest.TestCase):
    def test_buy_fill_has_positive_slippage(self):
        fill, slip = apply_buy_fill(100, 10)
        self.assertGreater(fill, 100)
        self.assertGreater(slip, 0)

    def test_sell_fill_has_negative_slippage(self):
        fill, slip = apply_sell_fill(100, 10)
        self.assertLess(fill, 100)
        self.assertGreater(slip, 0)

    def test_commission(self):
        self.assertEqual(commission_for(10000, 10), 10)

    def test_crossover_signal(self):
        closes = [10] * 30 + [11, 12, 13]
        signal = crossover_signal(closes, 3, 30)
        self.assertIn(signal, {"BUY", "SELL", "HOLD"})

    def test_max_drawdown(self):
        value, curve = max_drawdown([100, 120, 90, 110])
        self.assertAlmostEqual(value, 25.0)
        self.assertEqual(len(curve), 4)

    def test_trade_statistics(self):
        stats = trade_statistics([
            {"net_pnl": 100},
            {"net_pnl": -50},
        ])
        self.assertEqual(stats["win_rate_pct"], 50.0)
        self.assertEqual(stats["profit_factor"], 2.0)

    def test_backtest_runs(self):
        result = run_backtest("AAPL", sample_bars(), {
            "initial_cash": 100000,
            "fast_period": 5,
            "slow_period": 15,
            "position_fraction": 0.9,
            "slippage_bps": 2,
            "commission_bps": 1,
        })
        self.assertEqual(result["symbol"], "AAPL")
        self.assertEqual(result["bar_count"], 180)
        self.assertGreaterEqual(
            result["trade_statistics"]["total_trades"], 1
        )

    def test_backtest_safety(self):
        result = run_backtest("AAPL", sample_bars(), {
            "fast_period": 5,
            "slow_period": 15,
        })
        self.assertTrue(result["paper_only"])
        self.assertFalse(result["broker_write_enabled"])
        self.assertFalse(result["order_submission_enabled"])


if __name__ == "__main__":
    unittest.main()
