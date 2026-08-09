from pathlib import Path
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from market_data_engine.models import Bar
from broker_integration_v1.bootstrap_live_continuity_validation_v2_1_9 import (
    merge_bootstrap_and_live_bars,
    BootstrapLiveContinuityValidatorV219,
)
from broker_integration_v1.bootstrap_live_continuity_validation_status_v2_1_9 import (
    build_v2_1_9_status,
)

def b(symbol,minute,close):
    t=datetime(2026,8,7,19,57,tzinfo=timezone.utc)+timedelta(minutes=minute)
    c=Decimal(str(close))
    return Bar(
        symbol=symbol,timestamp=t,
        open=c,high=c+1,low=c-1,close=c,
        volume=100+minute,trade_count=10+minute,vwap=c
    )

class FakeBootstrap:
    def fetch_recent_completed_bars(self,symbols,bars_per_symbol=3,lookback_days=7):
        return {
            s:[b(s,0,100),b(s,1,101),b(s,2,102)]
            for s in symbols
        }

class TestV219(unittest.TestCase):
    def test_duplicate_timestamp_live_replaces_bootstrap(self):
        old=b("AAPL",2,102)
        live=b("AAPL",2,999)
        m=merge_bootstrap_and_live_bars(
            [b("AAPL",0,100),b("AAPL",1,101),old],
            [live],
            50,
        )
        self.assertEqual(m["per_symbol_counts"]["AAPL"],3)
        self.assertTrue(m["duplicate_free"])
        self.assertEqual(m["bars"][-1].close,Decimal("999"))

    def test_chronological_merge(self):
        m=merge_bootstrap_and_live_bars(
            [b("AAPL",0,100),b("AAPL",2,102)],
            [b("AAPL",1,101),b("AAPL",3,103)],
            50,
        )
        ts=[x.timestamp for x in m["bars"]]
        self.assertEqual(ts,sorted(ts))
        self.assertTrue(m["monotonic"])

    def test_bounded_retention(self):
        rows=[b("AAPL",i,100+i) for i in range(8)]
        m=merge_bootstrap_and_live_bars(rows,[],3)
        self.assertEqual(m["per_symbol_counts"]["AAPL"],3)

    def test_bootstrap_then_live_signal_recalculation(self):
        v=BootstrapLiveContinuityValidatorV219(
            ["AAPL","SPY"],
            bootstrap_client=FakeBootstrap(),
        )
        base=v.bootstrap_only()
        live=[
            b("AAPL",3,104),
            b("SPY",3,99),
        ]
        result=v.validate_with_live_bars(
            base["bootstrap_bars"],
            live,
        )
        self.assertEqual(result["status"],"PASS_BOOTSTRAP_LIVE_CONTINUITY")
        self.assertTrue(result["duplicate_free"])
        self.assertTrue(result["monotonic"])
        self.assertEqual(result["broker_orders_submitted"],0)

    def test_status_locks(self):
        s=build_v2_1_9_status()
        self.assertTrue(s["timestamp_deduplication"])
        self.assertTrue(s["signal_recalculation_after_merge"])
        self.assertFalse(s["broker_order_submission_from_stage"])
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["live_trading_enabled"])

if __name__=="__main__":
    unittest.main()
