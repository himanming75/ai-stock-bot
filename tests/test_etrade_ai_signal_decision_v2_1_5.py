from pathlib import Path
from decimal import Decimal
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.etrade_ai_signal_decision_v2_1_5 import (
    normalize_strategy_recommendation,
    decide_signal,
    SignalDecisionPolicy,
)
from broker_integration_v1.etrade_ai_signal_bridge_v2_1_5 import (
    ETradeAISignalDecisionBridge,
)
from broker_integration_v1.etrade_ai_signal_decision_status_v2_1_5 import (
    build_etrade_ai_signal_decision_v2_1_5_status,
)

class TestV215(unittest.TestCase):
    def test_buy_passes(self):
        r=normalize_strategy_recommendation({
            "symbol":"aapl","action":"buy","confidence":"0.80",
            "quantity":"1","strategy_id":"TEST"
        })
        d=decide_signal(r,SignalDecisionPolicy(Decimal("0.60")))
        self.assertTrue(d["order_eligible"])
        self.assertEqual(d["decision"],"BUY")

    def test_hold_blocks(self):
        b=ETradeAISignalDecisionBridge()
        r=b.evaluate({
            "symbol":"AAPL","action":"HOLD","confidence":"0.99",
            "quantity":"5","strategy_id":"TEST"
        })
        self.assertFalse(r["order_eligible"])
        self.assertIsNone(r["sandbox_signal"])

    def test_low_confidence_blocks(self):
        b=ETradeAISignalDecisionBridge()
        r=b.evaluate({
            "symbol":"AAPL","action":"SELL","confidence":"0.40",
            "quantity":"1","strategy_id":"TEST"
        })
        self.assertEqual(r["decision"],"HOLD")
        self.assertFalse(r["order_eligible"])

    def test_queue_bounded_to_three(self):
        b=ETradeAISignalDecisionBridge()
        payloads=[
            {"symbol":"AAPL","action":"BUY","confidence":"0.9","quantity":"1","strategy_id":"A"},
            {"symbol":"MSFT","action":"BUY","confidence":"0.9","quantity":"1","strategy_id":"B"},
            {"symbol":"SPY","action":"SELL","confidence":"0.9","quantity":"1","strategy_id":"C"},
            {"symbol":"QQQ","action":"BUY","confidence":"0.9","quantity":"1","strategy_id":"D"},
        ]
        q=b.build_signal_queue(payloads,max_signals=3)
        self.assertEqual(q["eligible_signal_count"],3)
        self.assertEqual(len(q["signals"]),3)

    def test_status_locks(self):
        s=build_etrade_ai_signal_decision_v2_1_5_status()
        self.assertTrue(s["hold_blocks_order"])
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["live_trading_enabled"])
        self.assertFalse(s["profitability_validation"])

if __name__=="__main__":
    unittest.main()
