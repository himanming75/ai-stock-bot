from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
import sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from market_data_engine.models import Bar
from broker_integration_v1.alpaca_readonly_current_bar_collector_v2_1_7 import (
    AlpacaReadOnlyCurrentBarCollectorV217,
)
from broker_integration_v1.etrade_current_market_wait_diagnostic_status_v2_1_7_1 import (
    build_v2_1_7_1_wait_diagnostic_status,
)

def b(symbol):
    c=Decimal("100")
    return Bar(
        symbol=symbol,
        timestamp=datetime(2026,8,9,13,30,tzinfo=timezone.utc),
        open=c,high=c+1,low=c-1,close=c,
        volume=100,trade_count=10,vwap=c,
    )

class TestV2171(unittest.TestCase):
    def test_progress_line(self):
        c=AlpacaReadOnlyCurrentBarCollectorV217(
            ["AAPL","SPY"],
            bars_per_symbol=3,
        )
        c.window.add(b("AAPL"))
        text=c.progress_line()
        self.assertIn("AAPL 1/3",text)
        self.assertIn("SPY 0/3",text)

    def test_snapshot_safe(self):
        c=AlpacaReadOnlyCurrentBarCollectorV217(
            ["AAPL"],
            bars_per_symbol=3,
        )
        snap=c.diagnostic_snapshot()
        self.assertFalse(snap["connection_opened"])
        self.assertEqual(snap["parsed_bar_count"],0)

    def test_complete(self):
        c=AlpacaReadOnlyCurrentBarCollectorV217(
            ["AAPL"],
            bars_per_symbol=3,
        )
        for _ in range(3):
            c.window.add(b("AAPL"))
        self.assertTrue(c.complete())

    def test_status_safety(self):
        s=build_v2_1_7_1_wait_diagnostic_status()
        self.assertTrue(s["market_closed_claim_is_conservative"])
        self.assertFalse(s["broker_order_submission"])
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["live_trading_enabled"])

if __name__=="__main__":
    unittest.main()
