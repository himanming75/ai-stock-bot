from pathlib import Path
from datetime import datetime,timezone
import tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.paper_intraday_autonomous_session_controller_v2_1_24 import (
    PaperIntradayAutonomousSessionControllerV2124,
    SESSION_CONFIRMATION,
)
from broker_integration_v1.paper_intraday_autonomous_session_status_v2_1_24 import (
    build_v2_1_24_status,
)


class FakeValidator:
    def __init__(self,status):
        self.status=status
    def run_once(self):
        return {
            "status":self.status,
            "broker_orders_submitted":0,
            "production_order_submission":False,
            "live_trading":False,
        }


class FakeExec:
    def __init__(self,submit=False):
        self.submit=submit
        self.calls=0
    def build_plan(self):
        return {
            "status":"READY_FOR_BOUNDED_ALPACA_PAPER_SUBMISSION",
            "paper_order_submitted":False,
        }
    def execute_once(self,confirmation):
        self.calls+=1
        return {
            "status":(
                "PAPER_ORDER_SUBMITTED_BOUNDED"
                if self.submit
                else "BLOCKED_PAPER_PREFLIGHT"
            ),
            "paper_order_submitted":self.submit,
            "live_order_submitted":False,
        }


class FakeLife:
    def __init__(self):
        self.calls=0
    def monitor_once(self,**kwargs):
        self.calls+=1
        return {
            "status":"PASS_ORDER_POSITION_LIFECYCLE_READ_ONLY",
            "position_lifecycle_state":"POSITION_HOLD_READ_ONLY",
            "exit_order_submitted":False,
            "live_order_submitted":False,
        }


class Tests(unittest.TestCase):
    def fixed_now(self):
        return datetime(2026,8,10,15,0,tzinfo=timezone.utc)

    def test_dry_ready_never_submits(self):
        with tempfile.TemporaryDirectory() as td:
            ex=FakeExec(submit=True)
            c=PaperIntradayAutonomousSessionControllerV2124(
                td,
                validator_factory=lambda:FakeValidator(
                    "PASS_ACTUAL_INTRADAY_CANONICAL_READY"
                ),
                execution_factory=lambda:ex,
                lifecycle_factory=lambda:FakeLife(),
                sleep_fn=lambda _:None,
                now_fn=self.fixed_now,
            )
            r=c.run(mode="DRY",max_cycles=2,interval_seconds=1)
            self.assertEqual(r["paper_orders_submitted"],0)
            self.assertEqual(ex.calls,0)
            self.assertEqual(r["exit_orders_submitted"],0)

    def test_paper_requires_session_confirmation(self):
        with tempfile.TemporaryDirectory() as td:
            c=PaperIntradayAutonomousSessionControllerV2124(
                td,
                validator_factory=lambda:FakeValidator(
                    "PASS_ACTUAL_INTRADAY_CANONICAL_READY"
                ),
                sleep_fn=lambda _:None,
                now_fn=self.fixed_now,
            )
            r=c.run(mode="PAPER",session_confirmation="WRONG")
            self.assertEqual(
                r["status"],
                "BLOCKED_SESSION_CONFIRMATION_REQUIRED",
            )
            self.assertEqual(r["paper_orders_submitted"],0)

    def test_one_paper_order_max_and_lifecycle_runs(self):
        with tempfile.TemporaryDirectory() as td:
            ex=FakeExec(submit=True)
            life=FakeLife()
            c=PaperIntradayAutonomousSessionControllerV2124(
                td,
                validator_factory=lambda:FakeValidator(
                    "PASS_ACTUAL_INTRADAY_CANONICAL_READY"
                ),
                execution_factory=lambda:ex,
                lifecycle_factory=lambda:life,
                sleep_fn=lambda _:None,
                now_fn=self.fixed_now,
            )
            r=c.run(
                mode="PAPER",
                session_confirmation=SESSION_CONFIRMATION,
                max_cycles=3,
                interval_seconds=1,
            )
            self.assertEqual(r["paper_orders_submitted"],1)
            self.assertEqual(ex.calls,1)
            self.assertEqual(life.calls,1)
            self.assertEqual(r["exit_orders_submitted"],0)
            self.assertEqual(r["live_orders_submitted"],0)

    def test_outside_market_stops(self):
        with tempfile.TemporaryDirectory() as td:
            c=PaperIntradayAutonomousSessionControllerV2124(
                td,
                validator_factory=lambda:FakeValidator(
                    "WAITING_FOR_MARKET_SESSION"
                ),
                sleep_fn=lambda _:None,
                now_fn=self.fixed_now,
            )
            r=c.run(mode="DRY",max_cycles=10,interval_seconds=1)
            self.assertEqual(r["cycles_completed"],1)
            self.assertEqual(
                r["stop_reason"],
                "WAITING_FOR_MARKET_SESSION",
            )
            self.assertEqual(r["paper_orders_submitted"],0)

    def test_status_contract(self):
        s=build_v2_1_24_status()
        self.assertTrue(s["v2_1_21_validator_reused"])
        self.assertTrue(s["v2_1_22_paper_entry_reused"])
        self.assertTrue(s["v2_1_23_lifecycle_reused"])
        self.assertFalse(s["new_broker_adapter_created"])
        self.assertFalse(s["automatic_exit_order_write"])
        self.assertEqual(s["maximum_paper_orders_per_session"],1)
        self.assertEqual(s["install_test_paper_orders"],0)
        self.assertFalse(s["live_trading_enabled"])


if __name__=="__main__":
    unittest.main()
