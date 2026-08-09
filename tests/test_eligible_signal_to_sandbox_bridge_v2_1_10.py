from pathlib import Path
from decimal import Decimal
import tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from broker_integration_v1.etrade_sandbox_autonomous_cycle_v2_1_3 import SandboxCycleSignal
from broker_integration_v1.eligible_signal_to_sandbox_bridge_v2_1_10 import EligibleSignalToSandboxBridgeV2110
from broker_integration_v1.eligible_signal_to_sandbox_bridge_status_v2_1_10 import build_v2_1_10_status

class FakeCycle:
    def __init__(self): self.calls=[]
    def run_once(self,account_id_key,signal,client_order_id):
        self.calls.append((account_id_key,signal.symbol,signal.side))
        return {
            "status":"PASS_SANDBOX_AUTONOMOUS_CYCLE",
            "real_money_moved":False,
            "production_order_submission":False,
        }

def sr(signals):
    return {"decision_queue":{
        "signals":signals,
        "eligible_signal_count":len(signals),
        "hold_or_block_count":0,
        "max_signals":3,
    }}

class TestV2110(unittest.TestCase):
    def test_hold_zero_order(self):
        b=EligibleSignalToSandboxBridgeV2110()
        r=b.execute(
            signal_result=sr([]),
            account_id_key="acct",
            cycle_engine=FakeCycle(),
            root=".",
            cooldown_seconds=0,
            sleep_fn=lambda _:None,
        )
        self.assertEqual(r["submitted_cycle_count"],0)
        self.assertEqual(r["status"],"PASS_NO_ELIGIBLE_SIGNALS_NO_ORDER")

    def test_buy_sell_execute_bounded(self):
        sigs=[
            SandboxCycleSignal("AAPL","BUY",Decimal("1"),strategy_id="S1"),
            SandboxCycleSignal("SPY","SELL",Decimal("1"),strategy_id="S2"),
        ]
        c=FakeCycle()
        with tempfile.TemporaryDirectory() as td:
            r=EligibleSignalToSandboxBridgeV2110().execute(
                signal_result=sr(sigs),
                account_id_key="acct",
                cycle_engine=c,
                root=td,
                cooldown_seconds=0,
                sleep_fn=lambda _:None,
            )
        self.assertEqual(r["submitted_cycle_count"],2)
        self.assertEqual(r["successful_cycle_count"],2)

    def test_max_three(self):
        sigs=[SandboxCycleSignal(x,"BUY",Decimal("1"),strategy_id=x) for x in ["A","B","C","D"]]
        with self.assertRaises(ValueError):
            EligibleSignalToSandboxBridgeV2110().build_plan(sr(sigs))

    def test_status_locks(self):
        s=build_v2_1_10_status()
        self.assertTrue(s["hold_zero_order_enforced"])
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["live_trading_enabled"])

if __name__=="__main__": unittest.main()
