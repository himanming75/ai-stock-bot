from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from multi_timeframe_ai.engine import (
    TIMEFRAMES,
    analyze_symbol,
    classify_regime,
    classify_structure,
    score_timeframe,
)
from multi_timeframe_ai.service import (
    MultiTimeframeAICertificationService,
    _feature_set,
)


class Tests(unittest.TestCase):
    def test_supported_timeframes(self):
        self.assertEqual(
            list(TIMEFRAMES),
            ["1m", "3m", "5m", "15m", "30m", "1h", "1d"],
        )

    def test_regime_boundaries(self):
        self.assertEqual(classify_regime(0.75), "STRONG_BULL")
        self.assertEqual(classify_regime(0.30), "WEAK_BULL")
        self.assertEqual(classify_regime(0.00), "RANGE")
        self.assertEqual(classify_regime(-0.30), "WEAK_BEAR")
        self.assertEqual(classify_regime(-0.75), "STRONG_BEAR")

    def test_structure_detection(self):
        self.assertEqual(
            classify_structure(
                gap_percent=0.02,
                close_vs_range=0.5,
                volume_ratio=1.0,
                follow_through=0.0,
            ),
            "GAP_UP",
        )
        self.assertEqual(
            classify_structure(
                gap_percent=0.0,
                close_vs_range=0.9,
                volume_ratio=1.8,
                follow_through=-0.01,
            ),
            "FAKE_BREAKOUT",
        )

    def test_timeframe_scoring_contract(self):
        features = _feature_set(100.0, 0.8, 0.01)["5m"]
        result = score_timeframe("5m", features)
        self.assertIn(result["signal"], {"BUY", "SELL", "HOLD"})
        self.assertGreaterEqual(result["probability"], 0.5)
        self.assertGreaterEqual(result["expected_risk"], 0.0)

    def test_consensus_and_confidence(self):
        result = analyze_symbol(
            "TEST",
            _feature_set(100.0, 0.8, 0.01),
        )
        self.assertEqual(len(result["timeframes"]), 7)
        self.assertGreater(result["trend_alignment"], 0.5)
        self.assertLessEqual(
            result["confidence_calibration"]["calibrated_confidence"],
            1.0,
        )

    def test_missing_timeframe_rejected(self):
        features = _feature_set(100.0, 0.8, 0.01)
        del features["1m"]
        with self.assertRaises(ValueError):
            analyze_symbol("TEST", features)

    def test_certification(self):
        with tempfile.TemporaryDirectory() as d:
            result = MultiTimeframeAICertificationService().evaluate(
                output_dir=Path(d)
            )
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["market_regime_2_ready"])
            self.assertTrue(result["confidence_calibration_ready"])
            self.assertTrue(result["bilingual_report_ready"])

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as d:
            result = MultiTimeframeAICertificationService().evaluate(
                output_dir=Path(d)
            )
            self.assertFalse(result["actual_broker_write_performed"])
            self.assertFalse(result["actual_order_submission_performed"])
            self.assertFalse(result["actual_order_cancel_performed"])
            self.assertFalse(result["actual_position_allocation_performed"])
            self.assertEqual(result["actual_paper_orders_submitted"], 0)
            self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
