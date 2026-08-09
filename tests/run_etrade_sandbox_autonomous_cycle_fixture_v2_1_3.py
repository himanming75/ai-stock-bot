from pathlib import Path
from decimal import Decimal
import tempfile
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.etrade_sandbox_autonomous_cycle_v2_1_3 import SandboxCycleSignal,ETradeSandboxAutonomousCycle
from broker_integration_v1.etrade_sandbox_order_transport_v2_1 import FixtureSandboxOrderTransport

class R:
    def get_json(self,path):
        return {"OrdersResponse":{"Order":[{"orderId":222}]}}

account="SYNTHETIC"
t=FixtureSandboxOrderTransport({
    f"/accounts/{account}/orders/preview.json":{"PreviewOrderResponse":{"PreviewIds":[{"previewId":111}]}},
    f"/accounts/{account}/orders/place.json":{"PlaceOrderResponse":{"orderId":222}},
})
with tempfile.TemporaryDirectory() as td:
    result=ETradeSandboxAutonomousCycle(t,R(),td).run_once(
        account,
        SandboxCycleSignal("AAPL","BUY",Decimal("1")),
        "AUTO001",
    )
    print("STATUS:",result["status"])
    print("PREVIEW:",result["preview_status"])
    print("PLACE:",result["place_status"])
    print("RECONCILIATION:",result["reconciliation_status"])
    print("REAL MONEY:",result["real_money_moved"])
    if result["status"]!="PASS_SANDBOX_AUTONOMOUS_CYCLE":
        raise SystemExit(2)
print("V2.1.3 SYNTHETIC CYCLE: PASS")
