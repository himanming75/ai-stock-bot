from pathlib import Path
from decimal import Decimal
import tempfile
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.etrade_sandbox_autonomous_cycle_v2_1_3 import SandboxCycleSignal
from broker_integration_v1.etrade_sandbox_bounded_multi_cycle_v2_1_4 import (
    BoundedCyclePolicy,
    ETradeSandboxBoundedMultiCycleController,
)
from broker_integration_v1.etrade_sandbox_bounded_multi_cycle_status_v2_1_4 import (
    build_etrade_sandbox_bounded_multi_cycle_v2_1_4_status,
)

class FakeCycle:
    def __init__(self):
        self.calls=[]
    def run_once(self,account_id_key,signal,client_order_id):
        self.calls.append((account_id_key,signal.symbol,signal.side,client_order_id))
        return {
            "status":"PASS_SANDBOX_AUTONOMOUS_CYCLE",
            "real_money_moved":False,
            "production_order_submission":False,
        }

class ErrorCycle:
    def run_once(self,*args,**kwargs):
        raise RuntimeError("fixture")

class TestV214(unittest.TestCase):
    def test_max_three_cycles(self):
        signals=[
            SandboxCycleSignal("AAPL","BUY",Decimal("1")),
            SandboxCycleSignal("AAPL","SELL",Decimal("1")),
            SandboxCycleSignal("SPY","BUY",Decimal("1")),
            SandboxCycleSignal("QQQ","BUY",Decimal("1")),
        ]
        with tempfile.TemporaryDirectory() as td:
            c=FakeCycle()
            ctl=ETradeSandboxBoundedMultiCycleController(
                c,td,BoundedCyclePolicy(max_cycles=3,cooldown_seconds=0)
            )
            result=ctl.run("acct",signals)
            self.assertEqual(result["submitted_cycle_count"],3)
            self.assertEqual(result["stopped_reason"],"MAX_CYCLES_REACHED")

    def test_duplicate_guard(self):
        sig=SandboxCycleSignal("AAPL","BUY",Decimal("1"))
        with tempfile.TemporaryDirectory() as td:
            c=FakeCycle()
            ctl=ETradeSandboxBoundedMultiCycleController(
                c,td,BoundedCyclePolicy(max_cycles=3,cooldown_seconds=0)
            )
            result=ctl.run("acct",[sig,sig])
            self.assertEqual(result["submitted_cycle_count"],1)
            self.assertEqual(result["duplicate_signal_block_count"],1)

    def test_kill_switch(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeCycle()
            ctl=ETradeSandboxBoundedMultiCycleController(
                c,td,BoundedCyclePolicy(max_cycles=3,cooldown_seconds=0)
            )
            ctl.kill_switch_path.parent.mkdir(parents=True,exist_ok=True)
            ctl.kill_switch_path.write_text("STOP",encoding="utf-8")
            result=ctl.run(
                "acct",[SandboxCycleSignal("AAPL","BUY",Decimal("1"))]
            )
            self.assertEqual(result["submitted_cycle_count"],0)
            self.assertEqual(result["stopped_reason"],"KILL_SWITCH_ACTIVE")

    def test_fail_fast(self):
        with tempfile.TemporaryDirectory() as td:
            ctl=ETradeSandboxBoundedMultiCycleController(
                ErrorCycle(),td,BoundedCyclePolicy(max_cycles=3,cooldown_seconds=0)
            )
            result=ctl.run(
                "acct",[SandboxCycleSignal("AAPL","BUY",Decimal("1"))]
            )
            self.assertEqual(result["stopped_reason"],"CYCLE_ERROR")
            self.assertEqual(result["submitted_cycle_count"],1)

    def test_status_safety(self):
        s=build_etrade_sandbox_bounded_multi_cycle_v2_1_4_status()
        self.assertEqual(s["maximum_cycles"],3)
        self.assertFalse(s["unbounded_loop_allowed"])
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["live_trading_enabled"])

if __name__=="__main__":
    unittest.main()
