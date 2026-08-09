from pathlib import Path
from decimal import Decimal
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.etrade_sandbox_autonomous_cycle_v2_1_3 import (
    SandboxCycleSignal,
    ETradeSandboxAutonomousCycle,
    build_canonical_request,
)
from broker_integration_v1.etrade_sandbox_order_transport_v2_1 import FixtureSandboxOrderTransport
from broker_integration_v1.etrade_sandbox_autonomous_cycle_status_v2_1_3 import (
    build_etrade_sandbox_autonomous_cycle_v2_1_3_status,
)

class ReadFixture:
    def get_json(self,path):
        return {"OrdersResponse":{"Order":[{"orderId":222}]}}

class TestV213(unittest.TestCase):
    def test_build_canonical_request(self):
        r=build_canonical_request(SandboxCycleSignal("aapl","buy",Decimal("1")))
        self.assertEqual(r.symbol,"AAPL")
        self.assertEqual(str(r.quantity),"1")

    def test_one_cycle(self):
        account="TEST"
        pp=f"/accounts/{account}/orders/preview.json"
        pl=f"/accounts/{account}/orders/place.json"
        t=FixtureSandboxOrderTransport({
            pp:{"PreviewOrderResponse":{"PreviewIds":[{"previewId":111}]}},
            pl:{"PlaceOrderResponse":{"orderId":222}},
        })
        with tempfile.TemporaryDirectory() as td:
            c=ETradeSandboxAutonomousCycle(t,ReadFixture(),td)
            result=c.run_once(
                account,
                SandboxCycleSignal("AAPL","BUY",Decimal("1")),
                "AUTO001",
            )
            self.assertEqual(result["status"],"PASS_SANDBOX_AUTONOMOUS_CYCLE")
            self.assertEqual(result["reconciliation_status"],"MATCHED")
            self.assertFalse(result["real_money_moved"])

    def test_status_locks(self):
        s=build_etrade_sandbox_autonomous_cycle_v2_1_3_status()
        self.assertFalse(s["automatic_repeat_enabled"])
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["live_trading_enabled"])
        self.assertFalse(s["contracts"]["duplicate_order_engine_created"])

if __name__=="__main__":
    unittest.main()
