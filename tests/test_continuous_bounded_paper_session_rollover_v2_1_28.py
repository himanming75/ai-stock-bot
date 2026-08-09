from pathlib import Path
from datetime import datetime,timezone
import json,tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.continuous_bounded_paper_session_rollover_v2_1_28 import (
    ContinuousBoundedPaperSessionRolloverV2128,
    CONTINUOUS_SESSION_CONFIRMATION,
)
from broker_integration_v1.continuous_bounded_paper_session_status_v2_1_28 import (
    build_v2_1_28_status,
)


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
    (p/"cycle_state.json").write_text(
        json.dumps(state),
        encoding="utf-8",
    )
    return state


def append_completed(root, round_trip_id):
    p=Path(root)/"runtime"/"final_round_trip_ledger_v2_1_27"
    p.mkdir(parents=True,exist_ok=True)
    row={
        "status":"COMPLETED_ALPACA_PAPER_ROUND_TRIP",
        "round_trip_id":round_trip_id,
        "evidence_key":"ev-"+round_trip_id,
        "symbol":"AAPL",
    }
    with (p/"completed_round_trips.jsonl").open("a",encoding="utf-8") as f:
        f.write(json.dumps(row)+"\n")


class FakeCycle:
    def __init__(self, root, counter, outside=False):
        self.root=Path(root)
        self.counter=counter
        self.outside=outside

    def run(self, **kwargs):
        self.counter["cycle_calls"]+=1
        if self.outside:
            return {
                "status":"PASS_FULL_PAPER_ROUND_TRIP_ORCHESTRATION",
                "stop_reason":"WAITING_FOR_MARKET_SESSION",
                "paper_entry_count":0,
                "paper_exit_count":0,
            }

        n=self.counter["cycle_calls"]
        write_state(
            self.root,
            phase="ROUND_TRIP_EXIT_SUBMITTED",
            evidence_key=f"ev-{n}",
            symbol="AAPL",
            entry_submitted=True,
            entry_client_order_id=f"entry-{n}",
            position_observed=True,
            exit_ready=True,
            exit_submitted=True,
            round_trip_complete=False,
            paper_entry_count=1,
            paper_exit_count=1,
            live_order_count=0,
        )
        return {
            "status":"PASS_FULL_PAPER_ROUND_TRIP_ORCHESTRATION",
            "stop_reason":"EXIT_SUBMITTED_AWAITING_FINAL_FILL",
            "paper_entry_count":1,
            "paper_exit_count":1,
        }


class FakeFinalizer:
    def __init__(self, root, counter):
        self.root=Path(root)
        self.counter=counter

    def build_plan(self):
        return {
            "status":"READY_FOR_READ_ONLY_EXIT_FILL_RECONCILIATION",
        }

    def reconcile(self, **kwargs):
        self.counter["finalizer_calls"]+=1
        n=self.counter["finalizer_calls"]
        rid=f"rt-{n}"
        append_completed(self.root,rid)
        write_state(
            self.root,
            phase="ROUND_TRIP_COMPLETE",
            evidence_key=f"ev-{n}",
            symbol="AAPL",
            entry_submitted=True,
            entry_client_order_id=f"entry-{n}",
            position_observed=True,
            exit_ready=True,
            exit_submitted=True,
            round_trip_complete=True,
            paper_entry_count=1,
            paper_exit_count=1,
            live_order_count=0,
            final_round_trip_id=rid,
            final_fill_reconciled=True,
        )
        return {
            "status":"PASS_FINAL_EXIT_FILL_RECONCILIATION",
            "round_trip_id":rid,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        }


class Tests(unittest.TestCase):
    def fixed_now(self):
        return datetime(2026,8,10,15,30,tzinfo=timezone.utc)

    def test_no_rollover_when_cycle_not_complete(self):
        with tempfile.TemporaryDirectory() as td:
            write_state(td,phase="POSITION_HOLD")
            c=ContinuousBoundedPaperSessionRolloverV2128(
                td,now_fn=self.fixed_now
            )
            r=c.build_rollover_plan()
            self.assertEqual(
                r["status"],
                "NO_ROLLOVER_REQUIRED_CURRENT_CYCLE_NOT_COMPLETE",
            )
            self.assertFalse(r["rollover_allowed"])

    def test_rollover_requires_completed_ledger_proof(self):
        with tempfile.TemporaryDirectory() as td:
            write_state(
                td,
                phase="ROUND_TRIP_COMPLETE",
                round_trip_complete=True,
                final_round_trip_id="rt-proof",
                final_fill_reconciled=True,
            )
            c=ContinuousBoundedPaperSessionRolloverV2128(
                td,now_fn=self.fixed_now
            )
            r=c.build_rollover_plan()
            self.assertEqual(
                r["status"],
                "BLOCKED_ROLLOVER_COMPLETED_LEDGER_PROOF_MISSING",
            )

    def test_safe_rollover_preserves_ledgers(self):
        with tempfile.TemporaryDirectory() as td:
            write_state(
                td,
                phase="ROUND_TRIP_COMPLETE",
                round_trip_complete=True,
                final_round_trip_id="rt-1",
                final_fill_reconciled=True,
                paper_entry_count=1,
                paper_exit_count=1,
            )
            append_completed(td,"rt-1")
            completed_path=(
                Path(td)/"runtime"/"final_round_trip_ledger_v2_1_27"/
                "completed_round_trips.jsonl"
            )
            before=completed_path.read_text()

            c=ContinuousBoundedPaperSessionRolloverV2128(
                td,now_fn=self.fixed_now
            )
            r=c.rollover_once()

            self.assertEqual(r["status"],"PASS_SAFE_CYCLE_ROLLOVER")
            self.assertFalse(r["historical_ledgers_deleted"])
            self.assertEqual(completed_path.read_text(),before)

            state=json.loads(
                (
                    Path(td)/"runtime"/
                    "full_alpaca_paper_round_trip_v2_1_26"/
                    "cycle_state.json"
                ).read_text()
            )
            self.assertEqual(state["phase"],"IDLE")
            self.assertFalse(state["entry_submitted"])
            self.assertFalse(state["exit_submitted"])
            self.assertFalse(state["round_trip_complete"])
            self.assertEqual(state["paper_entry_count"],0)
            self.assertEqual(state["paper_exit_count"],0)
            self.assertEqual(
                state["prior_completed_round_trip_id"],
                "rt-1",
            )

    def test_paper_requires_continuous_confirmation(self):
        with tempfile.TemporaryDirectory() as td:
            c=ContinuousBoundedPaperSessionRolloverV2128(
                td,now_fn=self.fixed_now
            )
            r=c.run(
                mode="PAPER",
                confirmation="WRONG",
                max_supervisor_cycles=1,
                interval_seconds=1,
            )
            self.assertEqual(
                r["status"],
                "BLOCKED_CONTINUOUS_SESSION_CONFIRMATION_REQUIRED",
            )

    def test_two_round_trips_then_bounded_stop(self):
        with tempfile.TemporaryDirectory() as td:
            counter={"cycle_calls":0,"finalizer_calls":0}
            c=ContinuousBoundedPaperSessionRolloverV2128(
                td,
                cycle_factory=lambda:FakeCycle(td,counter),
                finalizer_factory=lambda:FakeFinalizer(td,counter),
                sleep_fn=lambda _:None,
                now_fn=self.fixed_now,
            )
            r=c.run(
                mode="PAPER",
                confirmation=CONTINUOUS_SESSION_CONFIRMATION,
                max_completed_round_trips=2,
                max_supervisor_cycles=10,
                interval_seconds=1,
                inner_cycle_max_cycles=1,
                finalizer_max_cycles=1,
            )
            self.assertEqual(
                r["status"],
                "PASS_CONTINUOUS_BOUNDED_PAPER_SESSION",
            )
            self.assertEqual(
                r["completed_round_trips_this_session"],
                2,
            )
            self.assertEqual(
                r["stop_reason"],
                "MAX_COMPLETED_ROUND_TRIPS_REACHED",
            )
            self.assertEqual(counter["cycle_calls"],2)
            self.assertEqual(counter["finalizer_calls"],2)
            self.assertEqual(r["live_orders"],0)

    def test_outside_session_stops_without_looping(self):
        with tempfile.TemporaryDirectory() as td:
            counter={"cycle_calls":0,"finalizer_calls":0}
            c=ContinuousBoundedPaperSessionRolloverV2128(
                td,
                cycle_factory=lambda:FakeCycle(
                    td,counter,outside=True
                ),
                finalizer_factory=lambda:FakeFinalizer(td,counter),
                sleep_fn=lambda _:None,
                now_fn=self.fixed_now,
            )
            r=c.run(
                mode="DRY",
                max_supervisor_cycles=10,
                interval_seconds=1,
            )
            self.assertEqual(
                r["stop_reason"],
                "WAITING_FOR_MARKET_SESSION",
            )
            self.assertEqual(counter["cycle_calls"],1)
            self.assertEqual(counter["finalizer_calls"],0)

    def test_local_status_no_network(self):
        with tempfile.TemporaryDirectory() as td:
            c=ContinuousBoundedPaperSessionRolloverV2128(
                td,now_fn=self.fixed_now
            )
            r=c.local_status()
            self.assertEqual(
                r["status"],
                "PASS_LOCAL_CONTINUOUS_SESSION_STATUS",
            )
            self.assertFalse(r["broker_network_used"])
            self.assertEqual(r["paper_orders_submitted"],0)

    def test_status_contract(self):
        s=build_v2_1_28_status()
        self.assertTrue(
            s["v2_1_26_round_trip_orchestrator_reused"]
        )
        self.assertTrue(s["v2_1_27_finalizer_reused"])
        self.assertTrue(
            s["completed_ledger_proof_required_before_rollover"]
        )
        self.assertTrue(s["historical_ledgers_preserved"])
        self.assertTrue(s["only_current_cycle_state_reset"])
        self.assertFalse(s["new_entry_engine_created"])
        self.assertFalse(s["new_exit_engine_created"])
        self.assertEqual(
            s["default_max_completed_round_trips_per_session"],
            2,
        )
        self.assertEqual(s["install_test_paper_orders"],0)
        self.assertFalse(s["live_trading_enabled"])


if __name__=="__main__":
    unittest.main()
