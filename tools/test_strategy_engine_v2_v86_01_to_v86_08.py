from __future__ import annotations

import unittest

from strategy_engine_v2.decision import classify_decision
from strategy_engine_v2.engine import evaluate_strategy
from strategy_engine_v2.models import SignalInput
from strategy_engine_v2.scoring import aggregate_signals


class StrategyEngineV2Tests(unittest.TestCase):
    def test_buy_decision(self):
        result = evaluate_strategy("AAPL", [
            SignalInput("RSI", 70, 1.0),
            SignalInput("MACD", 80, 1.0),
            SignalInput("VOLUME", 60, 1.0),
        ])
        self.assertEqual(result.decision, "BUY")

    def test_sell_decision(self):
        result = evaluate_strategy("AAPL", [
            SignalInput("RSI", -70, 1.0),
            SignalInput("MACD", -80, 1.0),
            SignalInput("VOLUME", -60, 1.0),
        ])
        self.assertEqual(result.decision, "SELL")

    def test_hold_decision(self):
        result = evaluate_strategy("AAPL", [
            SignalInput("RSI", 5, 1.0),
            SignalInput("MACD", -5, 1.0),
        ])
        self.assertEqual(result.decision, "HOLD")

    def test_watch_decision(self):
        decision = classify_decision(20, 30)
        self.assertEqual(decision, "WATCH")

    def test_disabled_signal_ignored(self):
        metrics = aggregate_signals([
            SignalInput("A", 100, 1.0, enabled=False),
            SignalInput("B", 0, 1.0),
        ])
        self.assertEqual(metrics["composite_score"], 0.0)

    def test_weighted_score(self):
        metrics = aggregate_signals([
            SignalInput("A", 100, 3.0),
            SignalInput("B", -100, 1.0),
        ])
        self.assertEqual(metrics["composite_score"], 50.0)

    def test_score_clamped(self):
        metrics = aggregate_signals([
            SignalInput("A", 500, 1.0),
        ])
        self.assertEqual(metrics["composite_score"], 100.0)

    def test_safety_defaults(self):
        result = evaluate_strategy("AAPL", [SignalInput("A", 50)])
        self.assertTrue(result.paper_only)
        self.assertFalse(result.broker_write_enabled)
        self.assertFalse(result.order_submission_enabled)
        self.assertFalse(result.live_trading_enabled)


if __name__ == "__main__":
    unittest.main()
