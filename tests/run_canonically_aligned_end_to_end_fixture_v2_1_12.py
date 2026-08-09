from pathlib import Path
from decimal import Decimal
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.canonically_aligned_end_to_end_runtime_v2_1_12 import (
    CanonicallyAlignedEndToEndRuntimeV2112,
)

class HoldValidator:
    def bootstrap_only(self,quantity=Decimal("1")):
        return {
            "status":"PASS_BOOTSTRAP_BASELINE",
            "bootstrap_counts":{
                "AAPL":3,
                "MSFT":3,
                "SPY":3,
            },
            "signal_result":{
                "decision_queue":{
                    "signals":[],
                    "eligible_signal_count":0,
                    "hold_or_block_count":3,
                    "max_signals":3,
                }
            },
        }

r=CanonicallyAlignedEndToEndRuntimeV2112(
    ["AAPL","MSFT","SPY"],
    validator=HoldValidator(),
).build_runtime_plan()

print("STATUS:",r["status"])
print("BOOTSTRAP:",r["bootstrap_status"])
print("CANONICAL ALIGNED:",r["canonical_gate_aligned"])
print("ELIGIBLE:",r["eligible_signal_count"])
print("REQUIRES OAUTH:",r["requires_etrade_oauth"])
print("BROKER ORDERS:",r["broker_orders_submitted"])
print("PROD:",r["production_order_submission"])
print("LIVE:",r["live_trading"])
assert r["canonical_gate_aligned"] is True
assert r["eligible_signal_count"]==0
assert r["requires_etrade_oauth"] is False
print("V2.1.12 SYNTHETIC END-TO-END: PASS")
