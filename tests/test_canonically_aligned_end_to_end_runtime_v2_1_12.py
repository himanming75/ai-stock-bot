from pathlib import Path
from decimal import Decimal
import tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.etrade_sandbox_autonomous_cycle_v2_1_3 import (
    SandboxCycleSignal,
)
from broker_integration_v1.canonically_aligned_end_to_end_runtime_v2_1_12 import (
    CanonicallyAlignedEndToEndRuntimeV2112,
)
from broker_integration_v1.canonically_aligned_end_to_end_runtime_status_v2_1_12 import (
    build_v2_1_12_status,
)


class FakeValidatorHold:
    def bootstrap_only(self,quantity=Decimal("1")):
        return {
            "status":"PASS_BOOTSTRAP_BASELINE",
            "bootstrap_counts":{"AAPL":3},
            "signal_result":{
                "decision_queue":{
                    "signals":[],
                    "eligible_signal_count":0,
                    "hold_or_block_count":1,
                    "max_signals":3,
                }
            },
        }


class FakeValidatorBuy:
    def bootstrap_only(self,quantity=Decimal("1")):
        return {
            "status":"PASS_BOOTSTRAP_BASELINE",
            "bootstrap_counts":{"AAPL":3},
            "signal_result":{
                "decision_queue":{
                    "signals":[
                        SandboxCycleSignal(
                            "AAPL","BUY",Decimal("1"),
                            strategy_id="TEST"
                        )
                    ],
                    "eligible_signal_count":1,
                    "hold_or_block_count":0,
                    "max_signals":3,
                }
            },
        }


class FakeCycle:
    def run_once(self,account_id_key,signal,client_order_id):
        return {
            "status":"PASS_SANDBOX_AUTONOMOUS_CYCLE",
            "real_money_moved":False,
            "production_order_submission":False,
        }


class TestV2112(unittest.TestCase):
    def test_hold_plan_requires_no_oauth(self):
        r=CanonicallyAlignedEndToEndRuntimeV2112(
            ["AAPL"],
            validator=FakeValidatorHold(),
        ).build_runtime_plan()
        self.assertEqual(
            r["status"],
            "PASS_END_TO_END_PLAN_NO_ORDER",
        )
        self.assertFalse(r["requires_etrade_oauth"])
        self.assertEqual(r["eligible_signal_count"],0)
        self.assertTrue(r["canonical_gate_aligned"])

    def test_buy_plan_requires_confirmation(self):
        r=CanonicallyAlignedEndToEndRuntimeV2112(
            ["AAPL"],
            validator=FakeValidatorBuy(),
        ).build_runtime_plan()
        self.assertEqual(
            r["status"],
            "PASS_END_TO_END_PLAN_ELIGIBLE_SANDBOX",
        )
        self.assertTrue(r["requires_etrade_oauth"])
        self.assertTrue(
            r["requires_explicit_sandbox_confirmation"]
        )

    def test_execute_reuses_bounded_controller_path(self):
        runtime=CanonicallyAlignedEndToEndRuntimeV2112(
            ["AAPL"],
            validator=FakeValidatorBuy(),
        )
        plan=runtime.build_runtime_plan()
        with tempfile.TemporaryDirectory() as td:
            result=runtime.execute_sandbox(
                plan=plan,
                account_id_key="acct",
                cycle_engine=FakeCycle(),
                root=td,
                cooldown_seconds=0,
                sleep_fn=lambda _:None,
            )
        self.assertEqual(result["submitted_cycle_count"],1)
        self.assertEqual(result["successful_cycle_count"],1)
        self.assertFalse(result["production_order_submission"])
        self.assertFalse(result["live_trading"])

    def test_status_locks(self):
        s=build_v2_1_12_status()
        self.assertTrue(s["hold_zero_oauth_zero_order"])
        self.assertEqual(s["maximum_sandbox_cycles"],3)
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["live_trading_enabled"])

if __name__=="__main__":
    unittest.main()
