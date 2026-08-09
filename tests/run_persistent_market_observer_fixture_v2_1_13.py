from pathlib import Path
from decimal import Decimal
import tempfile,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.persistent_market_observer_v2_1_13 import (
    PersistentMarketObserverV2113,
    ObservationPolicyV2113,
)

class R:
    def __init__(self): self.n=0
    def build_runtime_plan(self,quantity=Decimal("1")):
        self.n+=1
        return {
            "bootstrap_status":"PASS_BOOTSTRAP_BASELINE",
            "bootstrap_counts":{"AAPL":3,"MSFT":3,"SPY":3},
            "canonical_gate_aligned":True,
            "eligible_signal_count":0,
            "eligible_signals":[],
            "hold_only":True,
        }

with tempfile.TemporaryDirectory() as td:
    r=PersistentMarketObserverV2113(
        R(),
        td,
        ObservationPolicyV2113(
            max_iterations=5,
            interval_seconds=1,
            stop_after_unchanged=2,
        ),
        sleep_fn=lambda _:None,
    ).run()
    print("STATUS:",r["status"])
    print("OBSERVATIONS:",r["observation_count"])
    print("ELIGIBLE OBSERVATIONS:",r["eligible_observation_count"])
    print("STOPPED:",r["stopped_reason"])
    print("BROKER ORDERS:",r["broker_orders_submitted"])
    print("PROD:",r["production_order_submission"])
    print("LIVE:",r["live_trading"])
    assert r["broker_orders_submitted"]==0
print("V2.1.13 SYNTHETIC OBSERVER: PASS")
