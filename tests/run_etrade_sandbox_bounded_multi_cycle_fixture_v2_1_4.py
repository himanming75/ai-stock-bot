from pathlib import Path
from decimal import Decimal
import tempfile
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.etrade_sandbox_autonomous_cycle_v2_1_3 import SandboxCycleSignal
from broker_integration_v1.etrade_sandbox_bounded_multi_cycle_v2_1_4 import (
    BoundedCyclePolicy,ETradeSandboxBoundedMultiCycleController
)

class C:
    def run_once(self,account_id_key,signal,client_order_id):
        return {
            "status":"PASS_SANDBOX_AUTONOMOUS_CYCLE",
            "signal":signal.symbol,
            "real_money_moved":False,
            "production_order_submission":False,
        }

signals=[
    SandboxCycleSignal("AAPL","BUY",Decimal("1")),
    SandboxCycleSignal("AAPL","SELL",Decimal("1")),
    SandboxCycleSignal("SPY","BUY",Decimal("1")),
]
with tempfile.TemporaryDirectory() as td:
    result=ETradeSandboxBoundedMultiCycleController(
        C(),td,BoundedCyclePolicy(max_cycles=3,cooldown_seconds=0)
    ).run("SYNTHETIC",signals)
    print("STATUS:",result["status"])
    print("SUBMITTED:",result["submitted_cycle_count"])
    print("SUCCESSFUL:",result["successful_cycle_count"])
    print("STOPPED:",result["stopped_reason"])
    print("REAL MONEY:",result["real_money_moved"])
    if result["successful_cycle_count"]!=3:
        raise SystemExit(2)
print("V2.1.4 SYNTHETIC BOUNDED MULTI-CYCLE: PASS")
