from pathlib import Path
from datetime import datetime,timezone
import tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.full_alpaca_paper_round_trip_cycle_v2_1_26 import (
    FullAlpacaPaperRoundTripCycleV2126,
    FULL_CYCLE_CONFIRMATION,
)
from broker_integration_v1.full_alpaca_paper_round_trip_status_v2_1_26 import (
    build_v2_1_26_status,
)


class FakeValidator:
    def __init__(self,status):
        self.status=status
        self.calls=0
    def run_once(self):
        self.calls+=1
        return {
            "status":self.status,
            "broker_orders_submitted":0,
            "production_order_submission":False,
            "live_trading":False,
        }


class FakeEntry:
    def __init__(self,submit=True):
        self.submit=submit
        self.execute_calls=0
        self.plan_calls=0
    def build_plan(self):
        self.plan_calls+=1
        return {
            "status":"READY_FOR_BOUNDED_ALPACA_PAPER_SUBMISSION",
            "evidence_key":"ev1",
            "paper_order_submitted":False,
        }
    def execute_once(self,confirmation):
        self.execute_calls+=1
        if not self.submit:
            return {
                "status":"BLOCKED_PAPER_PREFLIGHT",
                "paper_order_submitted":False,
            }
        return {
            "status":"PAPER_ORDER_SUBMITTED_BOUNDED",
            "evidence_key":"ev1",
            "client_order_id":"paper-entry-1",
            "selected_candidate":{"symbol":"AAPL","side":"buy"},
            "paper_order_submitted":True,
            "live_order_submitted":False,
        }


class FakeLifecycle:
    def __init__(self,states):
        self.states=list(states)
        self.calls=0
    def monitor_once(self,**kwargs):
        self.calls+=1
        state=self.states[min(self.calls-1,len(self.states)-1)]
        return {
            "status":"PASS_ORDER_POSITION_LIFECYCLE_READ_ONLY",
            "position_lifecycle_state":state,
            "position_exit_decision":{
                "action":"EXIT" if state=="POSITION_EXIT_READY_READ_ONLY" else "HOLD",
                "reason":"TAKE_PROFIT" if state=="POSITION_EXIT_READY_READ_ONLY" else "NO_EXIT_TRIGGER",
            },
            "exit_order_submitted":False,
            "live_order_submitted":False,
        }


class FakeExit:
    def __init__(self,submit=True,recovered=False):
        self.submit=submit
        self.recovered=recovered
        self.execute_calls=0
        self.plan_calls=0
    def build_plan(self):
        self.plan_calls+=1
        return {
            "status":"READY_FOR_ONE_TIME_ALPACA_PAPER_EXIT",
            "paper_exit_order_submitted":False,
        }
    def execute_once(self,confirmation):
        self.execute_calls+=1
        if self.recovered:
            return {
                "status":"RECOVERED_POSITION_ALREADY_CLOSED_NO_DUPLICATE_EXIT",
                "paper_exit_order_submitted":False,
                "live_order_submitted":False,
                "recovery_guard_triggered":True,
            }
        return {
            "status":"PAPER_EXIT_ORDER_SUBMITTED_ONCE" if self.submit else "BLOCKED_PAPER_PREFLIGHT",
            "paper_exit_order_submitted":self.submit,
            "live_order_submitted":False,
        }


class Tests(unittest.TestCase):
    def fixed_now(self):
        return datetime(2026,8,10,15,0,tzinfo=timezone.utc)

    def test_dry_ready_never_executes_orders(self):
        with tempfile.TemporaryDirectory() as td:
            entry=FakeEntry()
            ex=FakeExit()
            c=FullAlpacaPaperRoundTripCycleV2126(
                td,
                validator_factory=lambda:FakeValidator("PASS_ACTUAL_INTRADAY_CANONICAL_READY"),
                entry_factory=lambda:entry,
                lifecycle_factory=lambda:FakeLifecycle(["POSITION_HOLD_READ_ONLY"]),
                exit_factory=lambda:ex,
                sleep_fn=lambda _:None,
                now_fn=self.fixed_now,
            )
            r=c.run(mode="DRY",max_cycles=2,interval_seconds=1)
            self.assertEqual(r["paper_entry_count"],0)
            self.assertEqual(r["paper_exit_count"],0)
            self.assertEqual(entry.execute_calls,0)
            self.assertEqual(ex.execute_calls,0)

    def test_paper_requires_full_cycle_confirmation(self):
        with tempfile.TemporaryDirectory() as td:
            c=FullAlpacaPaperRoundTripCycleV2126(
                td,
                now_fn=self.fixed_now,
            )
            r=c.run(mode="PAPER",confirmation="WRONG")
            self.assertEqual(r["status"],"BLOCKED_FULL_CYCLE_CONFIRMATION_REQUIRED")
            self.assertEqual(r["paper_entry_count"],0)
            self.assertEqual(r["paper_exit_count"],0)

    def test_full_fake_entry_hold_exit_one_each(self):
        with tempfile.TemporaryDirectory() as td:
            validator=FakeValidator("PASS_ACTUAL_INTRADAY_CANONICAL_READY")
            entry=FakeEntry()
            life=FakeLifecycle([
                "POSITION_HOLD_READ_ONLY",
                "POSITION_EXIT_READY_READ_ONLY",
            ])
            ex=FakeExit()

            c=FullAlpacaPaperRoundTripCycleV2126(
                td,
                validator_factory=lambda:validator,
                entry_factory=lambda:entry,
                lifecycle_factory=lambda:life,
                exit_factory=lambda:ex,
                sleep_fn=lambda _:None,
                now_fn=self.fixed_now,
            )
            r=c.run(
                mode="PAPER",
                confirmation=FULL_CYCLE_CONFIRMATION,
                max_cycles=4,
                interval_seconds=1,
            )
            self.assertEqual(r["paper_entry_count"],1)
            self.assertEqual(r["paper_exit_count"],1)
            self.assertEqual(entry.execute_calls,1)
            self.assertEqual(ex.execute_calls,1)
            self.assertEqual(r["live_order_count"],0)
            self.assertEqual(r["stop_reason"],"EXIT_SUBMITTED_AWAITING_FINAL_FILL")

    def test_restart_recovery_does_not_reenter(self):
        with tempfile.TemporaryDirectory() as td:
            entry=FakeEntry()
            life=FakeLifecycle(["POSITION_EXIT_READY_READ_ONLY"])
            ex=FakeExit(recovered=True)

            c=FullAlpacaPaperRoundTripCycleV2126(
                td,
                validator_factory=lambda:FakeValidator("PASS_ACTUAL_INTRADAY_CANONICAL_READY"),
                entry_factory=lambda:entry,
                lifecycle_factory=lambda:life,
                exit_factory=lambda:ex,
                sleep_fn=lambda _:None,
                now_fn=self.fixed_now,
            )
            state=c._default_state()
            state.update({
                "phase":"ENTRY_SUBMITTED",
                "entry_submitted":True,
                "paper_entry_count":1,
                "evidence_key":"ev1",
                "symbol":"AAPL",
            })
            c._save_state(state)

            r=c.run(
                mode="PAPER",
                confirmation=FULL_CYCLE_CONFIRMATION,
                max_cycles=2,
                interval_seconds=1,
            )
            self.assertEqual(entry.execute_calls,0)
            self.assertEqual(ex.execute_calls,1)
            self.assertTrue(r["state"]["round_trip_complete"])
            self.assertEqual(r["stop_reason"],"ROUND_TRIP_COMPLETE")

    def test_outside_session_stops_without_entry(self):
        with tempfile.TemporaryDirectory() as td:
            entry=FakeEntry()
            c=FullAlpacaPaperRoundTripCycleV2126(
                td,
                validator_factory=lambda:FakeValidator("WAITING_FOR_MARKET_SESSION"),
                entry_factory=lambda:entry,
                sleep_fn=lambda _:None,
                now_fn=self.fixed_now,
            )
            r=c.run(mode="DRY",max_cycles=10,interval_seconds=1)
            self.assertEqual(r["stop_reason"],"WAITING_FOR_MARKET_SESSION")
            self.assertEqual(r["cycles_completed"],1)
            self.assertEqual(entry.execute_calls,0)

    def test_local_recovery_snapshot_no_network(self):
        with tempfile.TemporaryDirectory() as td:
            c=FullAlpacaPaperRoundTripCycleV2126(
                td,
                now_fn=self.fixed_now,
            )
            r=c.local_recovery_snapshot()
            self.assertEqual(r["status"],"PASS_LOCAL_FULL_CYCLE_RECOVERY_SNAPSHOT")
            self.assertFalse(r["broker_network_used"])
            self.assertEqual(r["paper_orders_submitted_from_stage"],0)

    def test_status_contract(self):
        s=build_v2_1_26_status()
        self.assertTrue(s["v2_1_21_validator_reused"])
        self.assertTrue(s["v2_1_22_entry_reused"])
        self.assertTrue(s["v2_1_23_lifecycle_reused"])
        self.assertTrue(s["v2_1_25_exit_recovery_reused"])
        self.assertTrue(s["recovery_first_state_machine"])
        self.assertEqual(s["maximum_paper_entries_per_cycle"],1)
        self.assertEqual(s["maximum_paper_exits_per_cycle"],1)
        self.assertEqual(s["install_test_paper_orders"],0)
        self.assertFalse(s["live_trading_enabled"])


if __name__=="__main__":
    unittest.main()
