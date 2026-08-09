from pathlib import Path
import sys,unittest
from decimal import Decimal

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from broker_integration_v1.etrade_canonical_signal_source_bridge_v2_1_6 import (
    CanonicalSignalSourceBridgeV216,canonical_signal_to_recommendation
)
from broker_integration_v1.etrade_canonical_signal_source_status_v2_1_6 import (
    build_etrade_canonical_signal_source_v2_1_6_status
)

def row(symbol,ts,close,macd,sig,roc,stoch,lo=90,hi=110):
    return {
        "symbol":symbol,"timeframe":"1Day","timestamp":ts,"source_close":close,
        "indicators":{
            "macd":macd,"macd_signal":sig,"roc":roc,"stochastic_k":stoch,
            "bollinger_lower":lo,"bollinger_upper":hi,
        }
    }

class TestV216(unittest.TestCase):
    def test_reuses_canonical_signal_engine(self):
        b=CanonicalSignalSourceBridgeV216()
        result=b.from_indicator_rows([
            row("AAPL","2026-08-01T00:00:00Z",100,2,1,1,20),
            row("AAPL","2026-08-02T00:00:00Z",100,2,1,1,20),
            row("MSFT","2026-08-02T00:00:00Z",100,1,2,-1,80),
        ])
        self.assertEqual(len(result["latest_signal_rows"]),2)
        self.assertEqual(result["network_requests_executed"],0)
        self.assertEqual(result["broker_orders_submitted"],0)

    def test_buy_recommendation_contract(self):
        x=canonical_signal_to_recommendation({
            "symbol":"aapl","signal":"BUY","confidence":0.8,
            "timestamp":"t","timeframe":"1Day","score":3,"reasons":["A","B"]
        })
        self.assertEqual(x["action"],"BUY")
        self.assertEqual(x["strategy_id"],"V79_71_75_CANONICAL_HISTORICAL_SIGNAL")

    def test_hold_never_enters_order_queue(self):
        b=CanonicalSignalSourceBridgeV216()
        result=b.from_indicator_rows([
            row("AAPL","2026-08-02T00:00:00Z",100,1,1,0,50),
        ])
        self.assertEqual(result["decision_queue"]["eligible_signal_count"],0)

    def test_queue_stays_bounded(self):
        b=CanonicalSignalSourceBridgeV216()
        rows=[row(x,"2026-08-02T00:00:00Z",100,2,1,1,20) for x in ["AAPL","MSFT","SPY","QQQ"]]
        result=b.from_indicator_rows(rows,max_signals=3)
        self.assertEqual(result["decision_queue"]["eligible_signal_count"],3)

    def test_status_locks(self):
        s=build_etrade_canonical_signal_source_v2_1_6_status()
        self.assertEqual(s["canonical_signal_engine_reused"],"V79.71-V79.75")
        self.assertFalse(s["network_market_data_enabled"])
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["live_trading_enabled"])

if __name__=="__main__": unittest.main()
