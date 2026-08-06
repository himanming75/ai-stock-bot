from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from ai_feature_engine.features import build_features
from ai_feature_engine.normalization import normalize_bars
from ai_feature_engine.service import (
    AIFeatureSignalCertificationService,
)
from ai_feature_engine.signals import generate_signal


class Tests(unittest.TestCase):
    def fixture(self, drift=0.3):
        price = 100.0
        rows = []
        for i in range(80):
            price += drift
            rows.append({
                "timestamp": str(i),
                "open": price - 0.2,
                "high": price + 0.6,
                "low": price - 0.6,
                "close": price,
                "volume": 1000 + i,
            })
        return rows

    def test_feature_engine(self):
        bars = normalize_bars(self.fixture())
        features = build_features(bars)
        for key in (
            "ema9","ema21","rsi14","macd_histogram",
            "vwap","atr14","bollinger_width",
            "momentum_5","volume_ratio",
        ):
            self.assertIn(key, features)

    def test_signal_candidate_no_order(self):
        bars = normalize_bars(self.fixture())
        candidate = generate_signal(
            symbol="AAPL",
            features=build_features(bars),
            configuration={
                "profile": {"max_daily_loss_percent": 1},
                "execution": {"activation_enabled": False},
            },
        )
        self.assertIn(candidate["action"], {"BUY","SELL","HOLD"})
        self.assertFalse(candidate["order_submission_enabled"])
        self.assertFalse(candidate["broker_write_enabled"])

    def test_unsafe_activation_blocked_by_gate(self):
        bars = normalize_bars(self.fixture())
        candidate = generate_signal(
            symbol="AAPL",
            features=build_features(bars),
            configuration={
                "profile": {"max_daily_loss_percent": 1},
                "execution": {"activation_enabled": True},
            },
        )
        self.assertEqual(
            candidate["risk_gate"],
            "BLOCKED_UNSAFE_ACTIVATION_FLAG",
        )

    def test_minimum_bars(self):
        with self.assertRaises(ValueError):
            normalize_bars(self.fixture()[:10])

    def test_certification(self):
        with tempfile.TemporaryDirectory() as d:
            result = AIFeatureSignalCertificationService().evaluate(
                output_dir=Path(d)
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["candidate_count"], 3)

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as d:
            result = AIFeatureSignalCertificationService().evaluate(
                output_dir=Path(d)
            )
            self.assertFalse(result["actual_broker_write_performed"])
            self.assertEqual(result["actual_paper_orders_submitted"], 0)
            self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
