from pathlib import Path
from datetime import datetime,timezone
import tempfile,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.persistent_market_observer_v2_1_13 import (
    ObservationPolicyV2113,
)
from broker_integration_v1.freshness_guarded_persistent_observer_v2_1_15 import (
    FreshnessGuardedPersistentObserverV2115,
)

class NeverCalled:
    def __init__(self): self.calls=0
    def build_runtime_plan(self,quantity=1,now_utc=None):
        self.calls+=1
        raise RuntimeError("should not be called")

runtime=NeverCalled()

with tempfile.TemporaryDirectory() as td:
    r=FreshnessGuardedPersistentObserverV2115(
        runtime,
        td,
        ObservationPolicyV2113(
            max_iterations=3,
            interval_seconds=1,
            stop_after_unchanged=2,
        ),
        sleep_fn=lambda _:None,
        now_fn=lambda:datetime(2026,8,9,16,0,tzinfo=timezone.utc),
    ).run()

    print("STATUS:",r["status"])
    print("OBSERVATIONS:",r["observation_count"])
    print("WAITING SESSION:",r["waiting_session_count"])
    print("RUNTIME CALLS:",r["market_data_runtime_call_count"])
    print("FETCH SKIPPED:",r["market_data_fetch_skipped_count"])
    print("ELIGIBLE CAPTURES:",r["eligible_capture_count"])
    print("BROKER ORDERS:",r["broker_orders_submitted"])
    print("PROD:",r["production_order_submission"])
    print("LIVE:",r["live_trading"])
    assert runtime.calls==0
    assert r["broker_orders_submitted"]==0
print("V2.1.15 SYNTHETIC INTEGRATION: PASS")
