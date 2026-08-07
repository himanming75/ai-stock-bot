from datetime import datetime, timezone
from pathlib import Path
import unittest

from tools.build_real_market_multitimeframe_shadow import (
    aggregate_daily,
    aggregate_intraday_by_session,
    feature_from_bars,
)

class Tests(unittest.TestCase):
    def _row(self, ts, price=100.0):
        return {
            "timestamp":ts,
            "open":price,
            "high":price+1,
            "low":price-1,
            "close":price+.25,
            "volume":100,
        }

    def test_daily_bar_one_session(self):
        sessions={
            "2026-08-03":[self._row("2026-08-03T13:30:00+00:00",100),self._row("2026-08-03T19:59:00+00:00",102)],
            "2026-08-04":[self._row("2026-08-04T13:30:00+00:00",103),self._row("2026-08-04T19:59:00+00:00",105)],
        }
        bars=aggregate_daily(sessions)
        self.assertEqual(len(bars),2)
        self.assertEqual(bars[0]["open"],100.0)
        self.assertEqual(bars[0]["close"],102.25)

    def test_intraday_does_not_cross_sessions(self):
        sessions={
            "d1":[self._row(f"2026-08-03T13:{30+i:02d}:00+00:00") for i in range(5)],
            "d2":[self._row(f"2026-08-04T13:{30+i:02d}:00+00:00") for i in range(5)],
        }
        bars=aggregate_intraday_by_session(sessions,3)
        self.assertEqual(len(bars),2)

    def test_daily_feature_allows_realistic_30_calendar_day_window(self):
        bars=[self._row(f"2026-07-{i:02d}T20:00:00+00:00",100+i) for i in range(1,22)]
        self.assertIsNotNone(feature_from_bars(bars,"1d"))

    def test_shadow_reuses_existing_canonical_functions(self):
        txt=Path("tools/build_real_market_multitimeframe_shadow.py").read_text(encoding="utf-8")
        self.assertIn("from multi_timeframe_ai.engine import analyze_symbol",txt)
        self.assertIn("from paper_autonomous_execution.signals import select_candidate",txt)
        self.assertNotIn("submit_order(",txt)
        self.assertNotIn("TradingClient(",txt)

if __name__=="__main__":
    unittest.main()
