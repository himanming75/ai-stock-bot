from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .full_alpaca_paper_round_trip_cycle_v2_1_26 import (
    FullAlpacaPaperRoundTripCycleV2126,
    FULL_CYCLE_CONFIRMATION,
)
from .final_exit_fill_reconciliation_round_trip_ledger_v2_1_27 import (
    FinalExitFillReconciliationRoundTripLedgerV2127,
)


CONTINUOUS_SESSION_CONFIRMATION="RUN_BOUNDED_CONTINUOUS_ALPACA_PAPER_SESSION"


class ContinuousBoundedPaperSessionRolloverV2128:
    """
    Thin orchestration/rollover layer over existing V2.1.26 + V2.1.27.

    This stage DOES NOT implement:
      - market data
      - canonical signals
      - entry order construction/submission
      - position lifecycle rules
      - exit order construction/submission
      - exit fill reconciliation math

    It only:
      1) resumes V2.1.26,
      2) invokes V2.1.27 when final exit fill reconciliation is pending,
      3) verifies a durable completed round-trip,
      4) preserves historical ledgers,
      5) resets ONLY V2.1.26 current-cycle state to a fresh IDLE state,
      6) starts the next bounded round-trip.

    Default safety limit: maximum 2 completed round-trips per session.
    """

    def __init__(
        self,
        root,
        *,
        cycle_factory=None,
        finalizer_factory=None,
        sleep_fn=None,
        now_fn=None,
    ):
        self.root=Path(root)
        self.cycle_factory=cycle_factory or (
            lambda:FullAlpacaPaperRoundTripCycleV2126(self.root)
        )
        self.finalizer_factory=finalizer_factory or (
            lambda:FinalExitFillReconciliationRoundTripLedgerV2127(self.root)
        )
        self.sleep_fn=sleep_fn or time.sleep
        self.now_fn=now_fn or (lambda:datetime.now(timezone.utc))

        self.v2126_state_path=(
            self.root/"runtime"/"full_alpaca_paper_round_trip_v2_1_26"/
            "cycle_state.json"
        )
        self.completed_ledger=(
            self.root/"runtime"/"final_round_trip_ledger_v2_1_27"/
            "completed_round_trips.jsonl"
        )

        self.runtime_dir=(
            self.root/"runtime"/"continuous_bounded_paper_session_v2_1_28"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.session_ledger=self.runtime_dir/"session_ledger.jsonl"
        self.rollover_ledger=self.runtime_dir/"rollover_ledger.jsonl"
        self.latest=self.runtime_dir/"latest_session.json"

    def _now(self):
        return self.now_fn().astimezone(timezone.utc)

    @staticmethod
    def _read_json(path):
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _read_v2126_state(self):
        if not self.v2126_state_path.exists():
            return None
        try:
            return self._read_json(self.v2126_state_path)
        except Exception:
            return None

    def _completed_rows(self):
        if not self.completed_ledger.exists():
            return []
        rows=[]
        for line in self.completed_ledger.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row=json.loads(line)
            except Exception:
                continue
            if row.get("status")=="COMPLETED_ALPACA_PAPER_ROUND_TRIP":
                rows.append(row)
        return rows

    def _completed_ids(self):
        return {
            str(r.get("round_trip_id"))
            for r in self._completed_rows()
            if r.get("round_trip_id")
        }

    def _append(self,path,row):
        with path.open("a",encoding="utf-8") as f:
            f.write(json.dumps(row,sort_keys=True,default=str)+"\n")

    def _write_latest(self,row):
        self.latest.write_text(
            json.dumps(row,indent=2,sort_keys=True,default=str),
            encoding="utf-8",
        )
        return row

    def _fresh_v2126_state(self, *, prior_round_trip_id=None):
        return {
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
            "prior_completed_round_trip_id":prior_round_trip_id,
            "rollover_by_stage":"V2.1.28",
            "updated_at_utc":self._now().isoformat(),
        }

    def build_rollover_plan(self):
        state=self._read_v2126_state()
        if state is None:
            return {
                "status":"NO_ROLLOVER_REQUIRED_NO_V2_1_26_STATE",
                "rollover_allowed":False,
                "broker_network_used":False,
            }

        if not state.get("round_trip_complete"):
            return {
                "status":"NO_ROLLOVER_REQUIRED_CURRENT_CYCLE_NOT_COMPLETE",
                "phase":state.get("phase"),
                "rollover_allowed":False,
                "broker_network_used":False,
            }

        round_trip_id=str(state.get("final_round_trip_id") or "").strip()
        if not round_trip_id:
            return {
                "status":"BLOCKED_ROLLOVER_FINAL_ROUND_TRIP_ID_MISSING",
                "rollover_allowed":False,
                "broker_network_used":False,
            }

        if not state.get("final_fill_reconciled"):
            return {
                "status":"BLOCKED_ROLLOVER_FINAL_FILL_NOT_RECONCILED",
                "round_trip_id":round_trip_id,
                "rollover_allowed":False,
                "broker_network_used":False,
            }

        if round_trip_id not in self._completed_ids():
            return {
                "status":"BLOCKED_ROLLOVER_COMPLETED_LEDGER_PROOF_MISSING",
                "round_trip_id":round_trip_id,
                "rollover_allowed":False,
                "broker_network_used":False,
            }

        return {
            "status":"READY_FOR_SAFE_CYCLE_ROLLOVER",
            "round_trip_id":round_trip_id,
            "prior_phase":state.get("phase"),
            "rollover_allowed":True,
            "historical_ledgers_preserved":True,
            "broker_network_used":False,
        }

    def rollover_once(self):
        plan=self.build_rollover_plan()
        if plan.get("status")!="READY_FOR_SAFE_CYCLE_ROLLOVER":
            return plan

        prior_state=self._read_v2126_state()
        round_trip_id=plan["round_trip_id"]

        new_state=self._fresh_v2126_state(
            prior_round_trip_id=round_trip_id
        )

        # Historical V2.1.22/V2.1.23/V2.1.25/V2.1.27 ledgers are untouched.
        # Only the current-cycle state file is replaced.
        self.v2126_state_path.parent.mkdir(parents=True,exist_ok=True)
        self.v2126_state_path.write_text(
            json.dumps(new_state,indent=2,sort_keys=True,default=str),
            encoding="utf-8",
        )

        row={
            "status":"PASS_SAFE_CYCLE_ROLLOVER",
            "rolled_over_at_utc":self._now().isoformat(),
            "completed_round_trip_id":round_trip_id,
            "prior_state":prior_state,
            "new_state":new_state,
            "historical_ledgers_deleted":False,
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        }
        self._append(self.rollover_ledger,row)
        return row

    def local_status(self):
        state=self._read_v2126_state()
        rows=self._completed_rows()
        return self._write_latest({
            "status":"PASS_LOCAL_CONTINUOUS_SESSION_STATUS",
            "v2_1_26_state":state,
            "completed_round_trip_count_total":len(rows),
            "completed_round_trip_ids":[
                r.get("round_trip_id") for r in rows
            ],
            "rollover_plan":self.build_rollover_plan(),
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        })

    def run(
        self,
        *,
        mode="DRY",
        confirmation="",
        max_completed_round_trips=2,
        max_supervisor_cycles=20,
        interval_seconds=30,
        inner_cycle_max_cycles=3,
        lifecycle_cycles=12,
        finalizer_max_cycles=12,
    ):
        mode=str(mode or "DRY").upper()
        if mode not in {"DRY","PAPER"}:
            raise ValueError("mode must be DRY or PAPER")
        if max_completed_round_trips<1 or max_completed_round_trips>3:
            raise ValueError(
                "max_completed_round_trips must be between 1 and 3"
            )
        if max_supervisor_cycles<1 or max_supervisor_cycles>200:
            raise ValueError(
                "max_supervisor_cycles must be between 1 and 200"
            )
        if interval_seconds<1:
            raise ValueError("interval_seconds must be >= 1")

        if (
            mode=="PAPER"
            and confirmation!=CONTINUOUS_SESSION_CONFIRMATION
        ):
            return self._write_latest({
                "status":"BLOCKED_CONTINUOUS_SESSION_CONFIRMATION_REQUIRED",
                "required_confirmation":CONTINUOUS_SESSION_CONFIRMATION,
                "mode":mode,
                "completed_round_trips_this_session":0,
                "paper_entry_orders_from_existing_stages":0,
                "paper_exit_orders_from_existing_stages":0,
                "live_orders":0,
            })

        baseline_ids=self._completed_ids()
        session_rows=[]
        stop_reason="MAX_SUPERVISOR_CYCLES"

        for supervisor_cycle in range(1,max_supervisor_cycles+1):
            current_ids=self._completed_ids()
            completed_this_session=len(current_ids-baseline_ids)

            if completed_this_session>=max_completed_round_trips:
                stop_reason="MAX_COMPLETED_ROUND_TRIPS_REACHED"
                break

            state=self._read_v2126_state()

            # If V2.1.27 already finalized a round trip, rollover locally.
            if state and state.get("round_trip_complete"):
                roll=self.rollover_once()
                session_rows.append({
                    "supervisor_cycle":supervisor_cycle,
                    "action":"ROLLOVER",
                    "result_status":roll.get("status"),
                    "round_trip_id":roll.get("completed_round_trip_id"),
                })
                if roll.get("status")!="PASS_SAFE_CYCLE_ROLLOVER":
                    stop_reason="ROLLOVER_BLOCKED"
                    break

            else:
                state=self._read_v2126_state()

                # V2.1.26 intentionally stops after exit submission.
                # V2.1.27 owns final exit fill reconciliation.
                if (
                    state
                    and state.get("exit_submitted")
                    and not state.get("round_trip_complete")
                ):
                    finalizer=self.finalizer_factory()
                    if mode=="DRY":
                        result=finalizer.build_plan()
                        session_rows.append({
                            "supervisor_cycle":supervisor_cycle,
                            "action":"DRY_FINAL_RECONCILIATION_PLAN",
                            "result_status":result.get("status"),
                        })
                    else:
                        result=finalizer.reconcile(
                            interval_seconds=5,
                            max_cycles=finalizer_max_cycles,
                        )
                        session_rows.append({
                            "supervisor_cycle":supervisor_cycle,
                            "action":"FINAL_RECONCILIATION",
                            "result_status":result.get("status"),
                            "round_trip_id":result.get("round_trip_id"),
                        })

                        if (
                            result.get("status")
                            =="PASS_FINAL_EXIT_FILL_RECONCILIATION"
                        ):
                            # Next supervisor iteration performs the verified
                            # local rollover.
                            pass
                        elif result.get("status") in {
                            "BLOCKED_EXIT_NOT_FILLED",
                            "BLOCKED_EXIT_FILLED_BUT_POSITION_REMAINS",
                            "BLOCKED_EXIT_BROKER_ORDER_ID_MISMATCH",
                            "BLOCKED_EXIT_FILL_FIELDS_INVALID",
                        }:
                            stop_reason="FINAL_RECONCILIATION_BLOCKED"
                            break

                else:
                    cycle=self.cycle_factory()
                    result=cycle.run(
                        mode=mode,
                        confirmation=(
                            FULL_CYCLE_CONFIRMATION
                            if mode=="PAPER"
                            else ""
                        ),
                        max_cycles=inner_cycle_max_cycles,
                        interval_seconds=max(1,interval_seconds),
                        lifecycle_cycles=lifecycle_cycles,
                    )
                    session_rows.append({
                        "supervisor_cycle":supervisor_cycle,
                        "action":"V2_1_26_ROUND_TRIP_STEP",
                        "result_status":result.get("status"),
                        "stop_reason":result.get("stop_reason"),
                        "paper_entry_count":result.get("paper_entry_count"),
                        "paper_exit_count":result.get("paper_exit_count"),
                    })

                    if result.get("stop_reason")=="WAITING_FOR_MARKET_SESSION":
                        stop_reason="WAITING_FOR_MARKET_SESSION"
                        break

            if supervisor_cycle<max_supervisor_cycles:
                self.sleep_fn(interval_seconds)

        final_ids=self._completed_ids()
        new_ids=sorted(final_ids-baseline_ids)

        result={
            "stage":
                "BROKER_INTEGRATION_V2_1_28_CONTINUOUS_BOUNDED_PAPER_SESSION_ROLLOVER",
            "status":"PASS_CONTINUOUS_BOUNDED_PAPER_SESSION",
            "mode":mode,
            "stop_reason":stop_reason,
            "supervisor_cycles_completed":len(session_rows),
            "max_completed_round_trips":max_completed_round_trips,
            "completed_round_trips_this_session":len(new_ids),
            "new_completed_round_trip_ids":new_ids,
            "session_rows":session_rows,
            "historical_round_trip_ledger_preserved":True,
            "v2_1_26_reused":True,
            "v2_1_27_reused":True,
            "new_entry_engine_created":False,
            "new_exit_engine_created":False,
            "live_orders":0,
            "live_trading_enabled":False,
            "completed_at_utc":self._now().isoformat(),
        }
        self._append(self.session_ledger,result)
        return self._write_latest(result)
