from pathlib import Path
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from market_data_engine.models import Bar
from broker_integration_v1.etrade_current_market_data_signal_bridge_v2_1_7 import (
    CurrentBarWindow,
    CurrentMarketDataSignalBridgeV217,
    bar_to_feature_row,
)
from broker_integration_v1.etrade_current_market_data_signal_status_v2_1_7 import (
    build_etrade_current_market_data_signal_v2_1_7_status,
)

def bar(symbol,i,close):
    t=datetime(2026,8,9,13,30,tzinfo=timezone.utc)+timedelta(minutes=i)
    c=Decimal(str(close))
    return Bar(
        symbol=symbol,timestamp=t,
        open=c,high=c+1,low=c-1,close=c,
        volume=100+i,trade_count=10+i,vwap=c
    )

class TestV217(unittest.TestCase):
    def test_bar_adapter(self):
        x=bar_to_feature_row(bar("AAPL",0,100))
        self.assertEqual(x["symbol"],"AAPL")
        self.assertEqual(x["features"]["volume"],100)

    def test_window_bounded(self):
        w=CurrentBarWindow(max_bars_per_symbol=3)
        for i in range(5): w.add(bar("AAPL",i,100+i))
        self.assertEqual(w.counts()["AAPL"],3)

    def test_current_bars_to_signal(self):
        bars=[
            bar("AAPL",0,100),
            bar("AAPL",1,101),
            bar("AAPL",2,103),
            bar("MSFT",0,100),
            bar("MSFT",1,99),
            bar("MSFT",2,97),
        ]
        result=CurrentMarketDataSignalBridgeV217().build_from_bars(bars)
        self.assertEqual(result["status"],"PASS_CURRENT_MARKET_DATA_TO_SIGNAL")
        self.assertEqual(result["broker_orders_submitted"],0)
        self.assertFalse(result["network_used_by_bridge"])

    def test_insufficient_bars_blocked(self):
        with self.assertRaises(ValueError):
            CurrentMarketDataSignalBridgeV217().build_from_bars([
                bar("AAPL",0,100),bar("AAPL",1,101)
            ])

    def test_status_locks(self):
        s=build_etrade_current_market_data_signal_v2_1_7_status()
        self.assertEqual(s["existing_market_data_engine_reused"],"V102.01-V103.00")
        self.assertFalse(s["broker_order_submission_from_stage"])
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["live_trading_enabled"])

if __name__=="__main__": unittest.main()
