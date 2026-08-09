from pathlib import Path
from decimal import Decimal
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker.contracts_v77_1 import BrokerOrderRequest, OrderSide, OrderType, TimeInForce
from broker_integration_v1.etrade_sandbox_order_builder_v2_1 import (
    build_equity_preview_payload, build_equity_place_payload, extract_preview_id, extract_order_id
)
from broker_integration_v1.etrade_sandbox_order_transport_v2_1 import (
    ETradeSandboxOrderTransport, FixtureSandboxOrderTransport, SandboxOrderPolicyError
)
from broker_integration_v1.etrade_sandbox_order_pipeline_v2_1 import ETradeSandboxOrderPipeline
from broker_integration_v1.etrade_sandbox_order_status_v2_1 import build_etrade_sandbox_order_v2_1_status

def req(order_type=OrderType.MARKET):
    kwargs={}
    if order_type is OrderType.LIMIT: kwargs["limit_price"]=Decimal("100")
    if order_type is OrderType.STOP: kwargs["stop_price"]=Decimal("90")
    if order_type is OrderType.STOP_LIMIT:
        kwargs["limit_price"]=Decimal("89"); kwargs["stop_price"]=Decimal("90")
    return BrokerOrderRequest(
        client_order_id="canonical001", symbol="AAPL", side=OrderSide.BUY,
        quantity=Decimal("1"), order_type=order_type, time_in_force=TimeInForce.DAY,
        strategy_id="TEST", **kwargs
    )

class TestV21(unittest.TestCase):
    def test_preview_reuses_canonical(self):
        p=build_equity_preview_payload(req(),"ABC123")
        self.assertEqual(p["PreviewOrderRequest"]["orderType"],"EQ")
    def test_market_payload(self):
        o=build_equity_preview_payload(req(),"ABC123")["PreviewOrderRequest"]["Order"][0]
        self.assertEqual(o["priceType"],"MARKET")
    def test_limit_payload(self):
        o=build_equity_preview_payload(req(OrderType.LIMIT),"ABC123")["PreviewOrderRequest"]["Order"][0]
        self.assertEqual(o["limitPrice"],"100")
    def test_place_preview_id(self):
        p=build_equity_preview_payload(req(),"ABC123")
        x=build_equity_place_payload(p,12345)
        self.assertEqual(x["PlaceOrderRequest"]["PreviewIds"][0]["previewId"],12345)
    def test_extractors(self):
        self.assertEqual(extract_preview_id({"PreviewOrderResponse":{"PreviewIds":[{"previewId":987}]}}),987)
        self.assertEqual(extract_order_id({"PlaceOrderResponse":{"orderId":765}}),"765")
    def test_default_network_locked(self):
        t=ETradeSandboxOrderTransport("k","s","t","ts",network_enabled=False)
        with self.assertRaises(SandboxOrderPolicyError):
            t.post_json("/accounts/A/orders/preview.json",{})
    def test_non_order_path_blocked(self):
        t=ETradeSandboxOrderTransport("k","s","t","ts",network_enabled=True)
        with self.assertRaises(SandboxOrderPolicyError):
            t._assert_sandbox_order_path("/market/quote/AAPL")
    def test_fixture(self):
        account="TESTKEY"
        pp=f"/accounts/{account}/orders/preview.json"
        pl=f"/accounts/{account}/orders/place.json"
        t=FixtureSandboxOrderTransport({
            pp:{"PreviewOrderResponse":{"PreviewIds":[{"previewId":111}]}},
            pl:{"PlaceOrderResponse":{"orderId":222}},
        })
        r=ETradeSandboxOrderPipeline(t).preview_and_place(account,req(),"ABC123")
        self.assertEqual(r["place"]["order_id"],"222")
        self.assertFalse(r["place"]["real_money_moved"])
    def test_status_prod_locked(self):
        s=build_etrade_sandbox_order_v2_1_status()
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["contracts"]["live_trading_enabled"])
    def test_not_profitability_validation(self):
        s=build_etrade_sandbox_order_v2_1_status()
        self.assertFalse(s["strategy_profitability_validated"])

if __name__=="__main__":
    unittest.main()
