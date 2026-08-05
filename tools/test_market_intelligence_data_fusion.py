from __future__ import annotations

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from market_intelligence.models import FusionInput
from market_intelligence.service import MarketIntelligenceFusionService


def sample(symbol: str = "AAA", **overrides) -> FusionInput:
    values = {
        "symbol": symbol,
        "price_return_1d": Decimal("0.02"),
        "price_return_5d": Decimal("0.08"),
        "volume_ratio": Decimal("1.8"),
        "realized_volatility": Decimal("0.24"),
        "relative_strength": Decimal("0.55"),
        "breadth_score": Decimal("0.30"),
        "sector_strength": Decimal("0.40"),
        "news_sentiment": Decimal("0.65"),
        "news_importance": Decimal("0.75"),
        "earnings_surprise": Decimal("0.20"),
        "earnings_revision": Decimal("0.15"),
        "macro_risk": Decimal("0.25"),
        "rates_pressure": Decimal("0.20"),
        "options_put_call": Decimal("0.85"),
        "options_iv_rank": Decimal("0.35"),
        "options_flow": Decimal("0.45"),
        "liquidity_score": Decimal("0.90"),
        "spread_bps": Decimal("3"),
        "event_risk": Decimal("0.15"),
        "source_confidence": Decimal("0.95"),
        "source_age_seconds": 30,
    }
    values.update(overrides)
    return FusionInput(**values)


class MarketIntelligenceTests(unittest.TestCase):
    def test_positive_market_ranks_symbols(self):
        context = MarketIntelligenceFusionService().fuse(
            [sample("AAA"), sample("BBB", price_return_5d=Decimal("0.02"))]
        )
        self.assertFalse(context.blockers)
        self.assertEqual(context.ranked_symbols[0].symbol, "AAA")

    def test_stale_source_blocks_symbol(self):
        context = MarketIntelligenceFusionService().fuse(
            [sample(source_age_seconds=5000)]
        )
        self.assertEqual(context.ranked_symbols[0].trade_bias, "BLOCKED")
        self.assertIn("SOURCE_DATA_TOO_STALE", context.ranked_symbols[0].blockers)

    def test_low_liquidity_hard_block(self):
        context = MarketIntelligenceFusionService().fuse(
            [sample(liquidity_score=Decimal("0.10"))]
        )
        self.assertIn("LIQUIDITY_HARD_BLOCK", context.ranked_symbols[0].blockers)

    def test_empty_input_is_blocked(self):
        context = MarketIntelligenceFusionService().fuse([])
        self.assertIn("NO_MARKET_DATA", context.blockers)

    def test_no_network_or_order_fields(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            source = base / "input.json"
            target = base / "output.json"
            source.write_text(
                '{"symbols":[{"symbol":"AAA","price_return_1d":"0.02",'
                '"price_return_5d":"0.08","volume_ratio":"1.8",'
                '"realized_volatility":"0.24","relative_strength":"0.55",'
                '"breadth_score":"0.30","sector_strength":"0.40",'
                '"news_sentiment":"0.65","news_importance":"0.75",'
                '"earnings_surprise":"0.20","earnings_revision":"0.15",'
                '"macro_risk":"0.25","rates_pressure":"0.20",'
                '"options_put_call":"0.85","options_iv_rank":"0.35",'
                '"options_flow":"0.45","liquidity_score":"0.90",'
                '"spread_bps":"3","source_confidence":"0.95"}]}',
                encoding="utf-8",
            )
            result = MarketIntelligenceFusionService().run_file(source, target)
            self.assertFalse(result["actual_external_network_used"])
            self.assertFalse(result["actual_order_submission_performed"])
            self.assertEqual(result["actual_paper_orders_submitted"], 0)
            self.assertTrue(target.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
