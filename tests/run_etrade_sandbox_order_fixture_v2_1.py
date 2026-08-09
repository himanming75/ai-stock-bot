from pathlib import Path
from decimal import Decimal
import sys, json
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from broker.contracts_v77_1 import BrokerOrderRequest, OrderSide, OrderType, TimeInForce
from broker_integration_v1.etrade_sandbox_order_transport_v2_1 import FixtureSandboxOrderTransport
from broker_integration_v1.etrade_sandbox_order_pipeline_v2_1 import ETradeSandboxOrderPipeline
account="SYNTHETIC"
pp=f"/accounts/{account}/orders/preview.json"
pl=f"/accounts/{account}/orders/place.json"
t=FixtureSandboxOrderTransport({
    pp:{"PreviewOrderResponse":{"PreviewIds":[{"previewId":314159}]}},
    pl:{"PlaceOrderResponse":{"orderId":271828}},
})
req=BrokerOrderRequest(client_order_id="fixture",symbol="AAPL",side=OrderSide.BUY,quantity=Decimal("1"),order_type=OrderType.MARKET,time_in_force=TimeInForce.DAY,strategy_id="SYNTHETIC")
r=ETradeSandboxOrderPipeline(t).preview_and_place(account,req,"SIM001")
print(json.dumps({"preview_id":r["preview"]["preview_id"],"order_id":r["place"]["order_id"],"real_money_moved":r["place"]["real_money_moved"]},indent=2))
if r["place"]["real_money_moved"]: raise SystemExit(2)
print("SANDBOX ORDER FIXTURE: PASS")
