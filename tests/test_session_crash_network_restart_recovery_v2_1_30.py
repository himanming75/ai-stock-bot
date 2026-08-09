from pathlib import Path
from datetime import datetime,timezone
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.session_crash_network_restart_recovery_v2_1_30 import (
    SessionCrashNetworkRestartRecoveryV2130,
    RECOVERY_SESSION_CONFIRMATION,
)
from broker_integration_v1.session_crash_network_restart_recovery_status_v2_1_30 import (
    build_v2_1_30_status,
)


def write_policy(root, attempts=3, delay=0):
    p=(
        Path(root)/"release"/
        "broker_integration_v2_1_30_session_crash_network_restart_recovery"/
        "config"
    )
    p.mkdir(parents=True,exist_ok=True)
    path=p/"recovery_policy.json"
    path.write_text(json.dumps({
        "policy_name":"TEST",
        "broker_read_max_attempts":attempts,
        "broker_read_retry_seconds":delay,
        "fail_closed_on_state_mismatch":True,
        "fail_closed_on_broker_unavailable":True,
        "paper_only":True,
        "live_trading":False,
    }),encoding="utf-8")
    return path


def write_state(root, **updates):
    p=Path(root)/"runtime"/"full_alpaca_paper_round_trip_v2_1_26"
    p.mkdir(parents=True,exist_ok=True)
    state={
        "version":"V2.1.26",
        "phase":"IDLE",
        "evidence_key":None,
        "symbol":None,
        "entry_submitted":False,
        "entry_client_order_id":None,
        "position_observed":False,
        "exit_ready":False,
        "exit_submitted":False,
        "round_trip_complete":False,
        "paper_entry_count":0,
        "paper_exit_count":0,
        "live_order_count":0,
    }
    state.update(updates)
    (p/"cycle_state.json").write_text(json.dumps(state),encoding="utf-8")
    return state


def write_exit(root, *, client_id="exit-client-1", broker_id="exit-broker-1"):
    p=Path(root)/"runtime"/"alpaca_paper_exit_recovery_v2_1_25"
    p.mkdir(parents=True,exist_ok=True)
    row={
        "status":"PAPER_EXIT_ORDER_SUBMITTED_ONCE",
        "evidence_key":"ev-1",
        "symbol":"AAPL",
        "paper_exit_order_submitted":True,
        "exit_order":{
            "id":broker_id,
            "client_order_id":client_id,
            "symbol":"AAPL",
            "status":"accepted",
            "paper":True,
        },
    }
    (p/"exit_ledger.jsonl").write_text(json.dumps(row)+"\n",encoding="utf-8")


class FakeClient:
    def __init__(
        self,
        *,
        positions=None,
        entry_status="filled",
        exit_status="accepted",
        fail_times=0,
        counter=None,
    ):
        self.positions=list(positions or [])
        self.entry_status=entry_status
        self.exit_status=exit_status
        self.fail_times=fail_times
        self.counter=counter if counter is not None else {"calls":0}

    def _maybe_fail(self):
        self.counter["calls"]+=1
        if self.counter["calls"]<=self.fail_times:
            raise TimeoutError("temporary network timeout")

    def get_positions(self):
        self._maybe_fail()
        return list(self.positions)

    def get_account(self):
        return {
            "status":"ACTIVE",
            "equity":"100000",
            "cash":"100000",
            "buying_power":"100000",
        }

    def get_clock(self):
        return {
            "is_open":True,
            "timestamp":"2026-08-10T15:00:00Z",
            "next_open":"2026-08-11T13:30:00Z",
            "next_close":"2026-08-10T20:00:00Z",
        }

    def get_order_by_client_id(self,client_order_id):
        status=(
            self.exit_status
            if str(client_order_id).startswith("exit")
            else self.entry_status
        )
        return {
            "id":"broker-"+client_order_id,
            "client_order_id":client_order_id,
            "symbol":"AAPL",
            "status":status,
            "filled_qty":"1" if status=="filled" else "0",
            "filled_avg_price":"100" if status=="filled" else None,
        }


class FakeRisk:
    def __init__(self):
        self.kills=[]
        self.run_calls=0

    def engage_kill_switch(self,reason):
        self.kills.append(reason)
        return {"status":"PASS_KILL_SWITCH_ENGAGED"}

    def run_guarded_session(self,**kwargs):
        self.run_calls+=1
        return {
            "status":"PASS_DAILY_RISK_GUARDED_SESSION",
            "stop_reason":"WAITING_FOR_MARKET_SESSION",
        }


class FakeRollover:
    def __init__(self,ready=True):
        self.ready=ready
        self.roll_calls=0

    def build_rollover_plan(self):
        return {
            "status":(
                "READY_FOR_SAFE_CYCLE_ROLLOVER"
                if self.ready
                else "BLOCKED_ROLLOVER_COMPLETED_LEDGER_PROOF_MISSING"
            )
        }

    def rollover_once(self):
        self.roll_calls+=1
        return {"status":"PASS_SAFE_CYCLE_ROLLOVER"}


class FakeFinalizer:
    def __init__(self,status="PASS_FINAL_EXIT_FILL_RECONCILIATION"):
        self.status=status
        self.calls=0

    def reconcile(self,**kwargs):
        self.calls+=1
        return {"status":self.status}


class Tests(unittest.TestCase):
    def fixed_now(self):
        return datetime(2026,8,10,15,0,tzinfo=timezone.utc)

    def make(self,td,client_factory=None,risk=None,roll=None,finalizer=None,attempts=3):
        return SessionCrashNetworkRestartRecoveryV2130(
            td,
            client_factory=client_factory or (lambda:FakeClient()),
            risk_factory=(lambda:risk) if risk else None,
            rollover_factory=(lambda:roll) if roll else None,
            finalizer_factory=(lambda:finalizer) if finalizer else None,
            sleep_fn=lambda _:None,
            now_fn=self.fixed_now,
            config_path=write_policy(td,attempts=attempts),
        )

    def test_no_state_local_idle(self):
        with tempfile.TemporaryDirectory() as td:
            c=self.make(td)
            r=c.local_plan()
            self.assertEqual(r["status"],"PASS_LOCAL_RECOVERY_PLAN")
            self.assertEqual(r["recovery_action"],"IDLE_START")
            self.assertFalse(r["broker_network_used"])

    def test_active_entry_local_resume_plan(self):
        with tempfile.TemporaryDirectory() as td:
            write_state(
                td,
                phase="ENTRY_SUBMITTED",
                symbol="AAPL",
                entry_submitted=True,
                entry_client_order_id="entry-client-1",
                paper_entry_count=1,
            )
            c=self.make(td)
            r=c.local_plan()
            self.assertEqual(
                r["recovery_action"],
                "RESUME_ENTRY_POSITION_LIFECYCLE",
            )

    def test_network_retry_recovers(self):
        with tempfile.TemporaryDirectory() as td:
            counter={"calls":0}
            def factory():
                return FakeClient(
                    fail_times=2,
                    counter=counter,
                )
            c=self.make(td,client_factory=factory,attempts=3)
            r=c.acquire_broker_snapshot()
            self.assertEqual(
                r["status"],
                "PASS_PAPER_BROKER_RECOVERY_SNAPSHOT",
            )
            self.assertEqual(r["attempts_used"],3)
            self.assertEqual(len(r["snapshot"]["retry_errors"]),2)
            self.assertFalse(r["broker_write_performed"])

    def test_network_retry_exhausted(self):
        with tempfile.TemporaryDirectory() as td:
            counter={"calls":0}
            def factory():
                return FakeClient(
                    fail_times=10,
                    counter=counter,
                )
            c=self.make(td,client_factory=factory,attempts=3)
            r=c.acquire_broker_snapshot()
            self.assertEqual(
                r["status"],
                "BLOCKED_BROKER_READ_RETRIES_EXHAUSTED",
            )
            self.assertEqual(r["attempts_used"],3)

    def test_idle_with_unknown_broker_position_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            write_state(td,phase="IDLE")
            c=self.make(
                td,
                client_factory=lambda:FakeClient(
                    positions=[{"symbol":"AAPL","qty":"1"}]
                ),
            )
            r=c.reconcile()
            self.assertEqual(
                r["status"],
                "BLOCKED_RECOVERY_STATE_MISMATCH",
            )
            self.assertIn(
                "BROKER_POSITION_EXISTS_WITH_NO_ACTIVE_LOCAL_CYCLE",
                r["mismatch_reasons"],
            )

    def test_entry_filled_with_position_resumes_v2126(self):
        with tempfile.TemporaryDirectory() as td:
            write_state(
                td,
                phase="ENTRY_SUBMITTED",
                symbol="AAPL",
                entry_submitted=True,
                entry_client_order_id="entry-client-1",
                paper_entry_count=1,
            )
            c=self.make(
                td,
                client_factory=lambda:FakeClient(
                    positions=[{"symbol":"AAPL","qty":"1"}],
                    entry_status="filled",
                ),
            )
            r=c.reconcile()
            self.assertEqual(
                r["status"],
                "PASS_RECOVERY_RECONCILIATION",
            )
            self.assertEqual(
                r["recovery_action"],
                "RESUME_V2_1_26_RECOVERY_FIRST",
            )

    def test_exit_submitted_routes_to_finalizer(self):
        with tempfile.TemporaryDirectory() as td:
            write_state(
                td,
                phase="ROUND_TRIP_EXIT_SUBMITTED",
                symbol="AAPL",
                entry_submitted=True,
                entry_client_order_id="entry-client-1",
                exit_submitted=True,
                paper_entry_count=1,
                paper_exit_count=1,
            )
            write_exit(td)
            c=self.make(
                td,
                client_factory=lambda:FakeClient(
                    positions=[],
                    entry_status="filled",
                    exit_status="filled",
                ),
            )
            r=c.reconcile()
            self.assertEqual(
                r["recovery_action"],
                "RUN_V2_1_27_FINAL_RECONCILIATION",
            )

    def test_completed_state_routes_to_rollover(self):
        with tempfile.TemporaryDirectory() as td:
            write_state(
                td,
                phase="ROUND_TRIP_COMPLETE",
                symbol="AAPL",
                round_trip_complete=True,
                final_round_trip_id="rt-1",
                final_fill_reconciled=True,
            )
            roll=FakeRollover(ready=True)
            c=self.make(
                td,
                client_factory=lambda:FakeClient(positions=[]),
                roll=roll,
            )
            r=c.reconcile()
            self.assertEqual(
                r["recovery_action"],
                "RUN_V2_1_28_SAFE_ROLLOVER",
            )

    def test_dry_recovery_never_writes(self):
        with tempfile.TemporaryDirectory() as td:
            write_state(td,phase="IDLE")
            risk=FakeRisk()
            c=self.make(td,risk=risk)
            r=c.recover_and_resume(mode="DRY")
            self.assertEqual(r["status"],"PASS_RECOVERY_DRY_PLAN")
            self.assertFalse(r["broker_write_performed"])
            self.assertEqual(r["paper_orders_submitted"],0)
            self.assertEqual(risk.run_calls,0)

    def test_paper_recovery_failure_engages_existing_kill(self):
        with tempfile.TemporaryDirectory() as td:
            write_state(td,phase="IDLE")
            risk=FakeRisk()
            c=self.make(
                td,
                client_factory=lambda:FakeClient(
                    positions=[{"symbol":"AAPL","qty":"1"}]
                ),
                risk=risk,
            )
            r=c.recover_and_resume(
                mode="PAPER",
                confirmation=RECOVERY_SESSION_CONFIRMATION,
                max_round_trips=1,
                interval_seconds=1,
            )
            self.assertEqual(r["status"],"BLOCKED_RECOVERY_RESUME")
            self.assertTrue(r["kill_switch_engaged"])
            self.assertEqual(
                risk.kills,
                ["V2_1_30_RECOVERY_FAIL_CLOSED"],
            )

    def test_paper_confirmation_required(self):
        with tempfile.TemporaryDirectory() as td:
            c=self.make(td)
            r=c.recover_and_resume(
                mode="PAPER",
                confirmation="WRONG",
            )
            self.assertEqual(
                r["status"],
                "BLOCKED_RECOVERY_SESSION_CONFIRMATION_REQUIRED",
            )

    def test_status_contract(self):
        s=build_v2_1_30_status()
        self.assertTrue(s["v2_1_26_recovery_first_state_reused"])
        self.assertTrue(s["v2_1_27_final_reconciliation_reused"])
        self.assertTrue(s["v2_1_28_rollover_reused"])
        self.assertTrue(s["v2_1_29_daily_risk_and_kill_switch_reused"])
        self.assertTrue(s["bounded_network_read_retry"])
        self.assertTrue(s["local_vs_broker_state_reconciliation"])
        self.assertTrue(s["mismatch_fail_closed"])
        self.assertFalse(s["new_trading_state_machine_created"])
        self.assertEqual(s["install_test_paper_orders"],0)
        self.assertFalse(s["live_trading_enabled"])


if __name__=="__main__":
    unittest.main()
