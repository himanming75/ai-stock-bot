import json
import tempfile
import unittest
from pathlib import Path

from market_context_v16_v20 import MarketContextIntelligence


class Tests(unittest.TestCase):
    def setup_root(self, root: Path):
        snapshot = (
            root
            / "runtime/market_context_inputs/"
              "latest_market_context_snapshot.json"
        )
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_text(json.dumps({
            "trend_score": 0.80,
            "volatility_risk": 0.40,
            "breadth_score": 0.70,
            "liquidity_score": 0.80,
            "sectors": {
                "XLK": {
                    "momentum": 0.90,
                    "breadth": 0.80,
                    "relative_strength": 0.85
                },
                "XLE": {
                    "momentum": 0.40,
                    "breadth": 0.45,
                    "relative_strength": 0.35
                }
            },
            "cross_asset": {
                "SPY": 0.02,
                "QQQ": 0.03,
                "VIX": -0.04,
                "TLT": -0.01
            },
            "volatility": {
                "realized": 0.35,
                "implied": 0.45,
                "short_term_forecast": 0.50
            },
            "breadth": {
                "advancers": 3000,
                "decliners": 1500,
                "above_50dma": 0.70,
                "new_highs": 200,
                "new_lows": 50
            }
        }), encoding="utf-8")

    def test_run_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = MarketContextIntelligence(root).run()
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(result["broker_write_performed"])

    def test_sector_rotation_has_leader(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = MarketContextIntelligence(root).sector_rotation()
            self.assertEqual(result["leading_sectors"][0], "XLK")

    def test_cross_asset_not_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = MarketContextIntelligence(
                root
            ).cross_asset_correlation()
            self.assertFalse(result["enforced"])

    def test_missing_snapshot_collects_data(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = MarketContextIntelligence(root).sector_rotation()
            self.assertEqual(result["status"], "COLLECTING_DATA")

    def test_breadth_score_range(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            score = MarketContextIntelligence(
                root
            ).market_breadth()["breadth_score"]
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 1)

    def test_outputs_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            MarketContextIntelligence(root).run()
            runtime = root / "runtime/market_context_v16_v20"
            self.assertTrue(
                (runtime / "latest_market_context_report.json").exists()
            )
            self.assertTrue(
                (runtime / "daily_market_context_summary.json").exists()
            )

    def test_live_write_off(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = MarketContextIntelligence(root).run()
            self.assertFalse(result["etrade_live_write_enabled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
