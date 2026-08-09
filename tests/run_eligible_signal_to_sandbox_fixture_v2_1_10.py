from pathlib import Path
from decimal import Decimal
import tempfile,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from broker_integration_v1.etrade_sandbox_autonomous_cycle_v2_1_3 import SandboxCycleSignal
from broker_integration_v1.eligible_signal_to_sandbox_bridge_v2_1_10 import EligibleSignalToSandboxBridgeV2110

class C:
    def run_once(self,account_id_key,signal,client_order_id):
        return {"status":"PASS_SANDBOX_AUTONOMOUS_CYCLE","real_money_moved":False,"production_order_submission":False}

signal_result={"decision_queue":{
    "signals":[
        SandboxCycleSignal("AAPL","BUY",Decimal("1"),strategy_id="FIXTURE"),
        SandboxCycleSignal("SPY","SELL",Decimal("1"),strategy_id="FIXTURE2"),
    ],
    "eligible_signal_count":2,"hold_or_block_count":1,"max_signals":3
}}

with tempfile.TemporaryDirectory() as td:
    r=EligibleSignalToSandboxBridgeV2110().execute(
        signal_result=signal_result,
        account_id_key="SYNTHETIC",
        cycle_engine=C(),
        root=td,
        cooldown_seconds=0,
        sleep_fn=lambda _:None,
    )
    print("STATUS:",r["status"])
    print("ELIGIBLE:",r["eligible_signal_count"])
    print("SUBMITTED:",r["submitted_cycle_count"])
    print("SUCCESSFUL:",r["successful_cycle_count"])
    print("PROD:",r["production_order_submission"])
    print("LIVE:",r["live_trading"])
    assert r["submitted_cycle_count"]==2
print("V2.1.10 SYNTHETIC BRIDGE: PASS")
