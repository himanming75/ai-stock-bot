from pathlib import Path
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from market_data_engine.models import Bar
from broker_integration_v1.alpaca_readonly_historical_bootstrap_v2_1_8 import (
    flatten_bootstrap_map,
)
from broker_integration_v1.historical_bootstrap_live_continuation_v2_1_8 import (
    HistoricalBootstrapLiveContinuationV218,
)
from broker_integration_v1.historical_bootstrap_live_continuation_status_v2_1_8 import (
    build_v2_1_8_status,
)

def b(symbol,i,close):
    t=datetime(2026,8,7,13,30,tzinfo=timezone.utc)+timedelta(minutes=i)
    c=Decimal(str(close))
    return Bar(
        symbol=symbol,timestamp=t,
        open=c,high=c+1,low=c-1,close=c,
        volume=100+i,trade_count=10+i,vwap=c
    )

class FakeBootstrap:
    def fetch_recent_completed_bars(self,symbols,bars_per_symbol=3,lookback_days=7):
        return {
            s:[b(s,0,100),b(s,1,101),b(s,2,103)]
            for s in symbols
        }

class TestV218(unittest.TestCase):
    def test_flatten(self):
        rows=flatten_bootstrap_map({
            "AAPL":[b("AAPL",0,100),b("AAPL",1,101)],
            "SPY":[b("SPY",0,100)],
        })
        self.assertEqual(len(rows),3)

    def test_bootstrap_signal_offline_fixture(self):
        o=HistoricalBootstrapLiveContinuationV218(
            ["AAPL","SPY"],
            bars_per_symbol=3,
            bootstrap_client=FakeBootstrap(),
        )
        r=o.bootstrap_signal()
        self.assertEqual(r["status"],"PASS_HISTORICAL_BOOTSTRAP_SIGNAL")
        self.assertEqual(r["broker_orders_submitted"],0)
        self.assertFalse(r["production_order_submission"])

    def test_status_locks(self):
        s=build_v2_1_8_status()
        self.assertTrue(s["historical_bootstrap_ready"])
        self.assertTrue(s["live_continuation_ready"])
        self.assertFalse(s["broker_order_submission_from_stage"])
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["live_trading_enabled"])

if __name__=="__main__":
    unittest.main()
