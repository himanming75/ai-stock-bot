from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .actual_intraday_canonical_e2e_validation_v2_1_21 import (
    ActualIntradayCanonicalEndToEndValidatorV2121,
)
from .alpaca_paper_bounded_execution_bridge_v2_1_22 import (
    AlpacaPaperBoundedExecutionBridgeV2122,
    CONFIRMATION_PHRASE as ENTRY_CONFIRMATION,
)
from .alpaca_paper_order_position_lifecycle_bridge_v2_1_23 import (
    AlpacaPaperOrderPositionLifecycleBridgeV2123,
)
from .alpaca_paper_exit_execution_recovery_guard_v2_1_25 import (
    AlpacaPaperExitExecutionRecoveryGuardV2125,
    EXIT_CONFIRMATION,
)


FULL_CYCLE_CONFIRMATION="RUN_FULL_ALPACA_PAPER_CYCLE"


class FullAlpacaPaperRoundTripCycleV2126:
    """
    Recovery-aware orchestration of the existing Broker Integration stages:

      V2.1.21 canonical intraday validation
      -> V2.1.22 bounded Alpaca Paper entry
      -> V2.1.23 read-only order/position lifecycle
      -> V2.1.25 one-time Alpaca Paper exit + recovery guard

    This class introduces no new signal, broker, order, or exit-strategy engine.

    DRY mode never calls entry/exit execute methods.
    PAPER mode requires FULL_CYCLE_CONFIRMATION and still inherits every
    V2.1.22 / V2.1.25 Paper-only preflight/arm/idempotency guard.
    """

    def __init__(
        self,
        root,
        *,
        validator_factory=None,
        entry_factory=None,
        lifecycle_factory=None,
        exit_factory=None,
        sleep_fn=None,
        now_fn=None,
    ):
        self.root=Path(root)
        self.validator_factory=validator_factory or (
            lambda:ActualIntradayCanonicalEndToEndValidatorV2121(self.root)
        )
        self.entry_factory=entry_factory or (
            lambda:AlpacaPaperBoundedExecutionBridgeV2122(self.root)
        )
        self.lifecycle_factory=lifecycle_factory or (
            lambda:AlpacaPaperOrderPositionLifecycleBridgeV2123(self.root)
        )
        self.exit_factory=exit_factory or (
            lambda:AlpacaPaperExitExecutionRecoveryGuardV2125(self.root)
        )
        self.sleep_fn=sleep_fn or time.sleep
        self.now_fn=now_fn or (lambda:datetime.now(timezone.utc))

        self.runtime_dir=(
            self.root/"runtime"/"full_alpaca_paper_round_trip_v2_1_26"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.state_path=self.runtime_dir/"cycle_state.json"
        self.ledger=self.runtime_dir/"cycle_ledger.jsonl"
        self.latest=self.runtime_dir/"latest_cycle.json"

    def _now(self):
        return self.now_fn().astimezone(timezone.utc)

    def _default_state(self):
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
            "updated_at_utc":self._now().isoformat(),
        }

    def _load_state(self):
        if not self.state_path.exists():
            return self._default_state()
        try:
            state=json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return self._default_state()
        base=self._default_state()
        base.update(state)
        return base

    def _save_state(self,state):
        state=dict(state)
        state["updated_at_utc"]=self._now().isoformat()
        self.state_path.write_text(
            json.dumps(state,indent=2,sort_keys=True,default=str),
            encoding="utf-8",
        )
        return state

    def _record(self,row):
        self.latest.write_text(
            json.dumps(row,indent=2,sort_keys=True,default=str),
            encoding="utf-8",
        )
        with self.ledger.open("a",encoding="utf-8") as f:
            f.write(json.dumps(row,sort_keys=True,default=str)+"\n")
        return row

    def local_recovery_snapshot(self):
        state=self._load_state()
        entry_ledger=(
            self.root/"runtime"/"alpaca_paper_bounded_execution_v2_1_22"/
            "execution_ledger.jsonl"
        )
        lifecycle_latest=(
            self.root/"runtime"/"alpaca_paper_order_position_lifecycle_v2_1_23"/
            "latest_lifecycle.json"
        )
        exit_ledger=(
            self.root/"runtime"/"alpaca_paper_exit_recovery_v2_1_25"/
            "exit_ledger.jsonl"
        )

        def count_rows(path,predicate=None):
            if not path.exists():
                return 0
            count=0
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    row=json.loads(line)
                except Exception:
                    continue
                if predicate is None or predicate(row):
                    count+=1
            return count

        result={
            "status":"PASS_LOCAL_FULL_CYCLE_RECOVERY_SNAPSHOT",
            "state":state,
            "v2_1_22_paper_entries":count_rows(
                entry_ledger,
                lambda r:r.get("paper_order_submitted") is True,
            ),
            "v2_1_23_lifecycle_snapshot_exists":lifecycle_latest.exists(),
            "v2_1_25_paper_exits":count_rows(
                exit_ledger,
                lambda r:r.get("paper_exit_order_submitted") is True,
            ),
            "broker_network_used":False,
            "paper_orders_submitted_from_stage":0,
            "live_orders_submitted_from_stage":0,
        }
        return self._record(result)

    def _update_from_entry(self,state,result):
        if result.get("paper_order_submitted") is True:
            state["phase"]="ENTRY_SUBMITTED"
            state["entry_submitted"]=True
            state["paper_entry_count"]=1
            state["evidence_key"]=result.get("evidence_key")
            state["entry_client_order_id"]=result.get("client_order_id")
            selected=result.get("selected_candidate") or {}
            state["symbol"]=selected.get("symbol")
        return self._save_state(state)

    def _update_from_lifecycle(self,state,result):
        lifecycle_state=result.get("position_lifecycle_state")
        if lifecycle_state:
            state["position_observed"]=True
        if lifecycle_state=="POSITION_EXIT_READY_READ_ONLY":
            state["phase"]="EXIT_READY"
            state["exit_ready"]=True
        elif lifecycle_state=="POSITION_HOLD_READ_ONLY":
            state["phase"]="POSITION_HOLD"
        return self._save_state(state)

    def _update_from_exit(self,state,result):
        status=result.get("status")
        if result.get("paper_exit_order_submitted") is True:
            state["phase"]="EXIT_SUBMITTED"
            state["exit_submitted"]=True
            state["paper_exit_count"]=1
        elif status=="RECOVERED_POSITION_ALREADY_CLOSED_NO_DUPLICATE_EXIT":
            state["phase"]="ROUND_TRIP_COMPLETE"
            state["round_trip_complete"]=True
        return self._save_state(state)

    def run(
        self,
        *,
        mode="DRY",
        confirmation="",
        max_cycles=3,
        interval_seconds=30,
        lifecycle_cycles=12,
    ):
        mode=str(mode or "DRY").upper()
        if mode not in {"DRY","PAPER"}:
            raise ValueError("mode must be DRY or PAPER")
        if max_cycles<1 or max_cycles>120:
            raise ValueError("max_cycles must be between 1 and 120")
        if interval_seconds<1:
            raise ValueError("interval_seconds must be >= 1")
        if lifecycle_cycles<1:
            raise ValueError("lifecycle_cycles must be >= 1")

        if mode=="PAPER" and confirmation!=FULL_CYCLE_CONFIRMATION:
            return self._record({
                "status":"BLOCKED_FULL_CYCLE_CONFIRMATION_REQUIRED",
                "required_confirmation":FULL_CYCLE_CONFIRMATION,
                "mode":mode,
                "paper_entry_count":0,
                "paper_exit_count":0,
                "live_order_count":0,
            })

        state=self._load_state()
        cycle_rows=[]
        stop_reason="MAX_CYCLES"

        for idx in range(1,max_cycles+1):
            row={"cycle":idx,"phase_before":state["phase"]}

            # Recovery-first: if an entry was already submitted, do not seek
            # another entry. Resume lifecycle/exit handling.
            if state["entry_submitted"] and not state["round_trip_complete"]:
                life=self.lifecycle_factory().monitor_once(
                    interval_seconds=5,
                    max_cycles=lifecycle_cycles,
                )
                row["lifecycle_status"]=life.get("status")
                row["position_lifecycle_state"]=life.get(
                    "position_lifecycle_state"
                )
                state=self._update_from_lifecycle(state,life)

                if state["exit_ready"]:
                    if mode=="DRY":
                        exit_plan=self.exit_factory().build_plan()
                        row["exit_plan_status"]=exit_plan.get("status")
                        row["action"]="DRY_EXIT_PLAN_ONLY"
                    elif state["paper_exit_count"]>=1:
                        row["action"]="EXIT_ALREADY_SUBMITTED_NO_DUPLICATE"
                    else:
                        exit_result=self.exit_factory().execute_once(
                            EXIT_CONFIRMATION
                        )
                        row["exit_status"]=exit_result.get("status")
                        row["paper_exit_order_submitted"]=bool(
                            exit_result.get("paper_exit_order_submitted")
                        )
                        state=self._update_from_exit(state,exit_result)
                        row["action"]="PAPER_EXIT_ATTEMPT"

                    cycle_rows.append(row)

                    if state["exit_submitted"]:
                        # V2.1.25 provides one-time durable submission state.
                        # This stage records the completed handoff; final broker
                        # fill confirmation will be added in the next stage.
                        state["phase"]="ROUND_TRIP_EXIT_SUBMITTED"
                        self._save_state(state)
                        stop_reason="EXIT_SUBMITTED_AWAITING_FINAL_FILL"
                        break

                    if state["round_trip_complete"]:
                        stop_reason="ROUND_TRIP_COMPLETE"
                        break
                else:
                    row["action"]="POSITION_MONITOR_ONLY"
                    cycle_rows.append(row)

            elif state["round_trip_complete"]:
                row["action"]="ROUND_TRIP_ALREADY_COMPLETE"
                cycle_rows.append(row)
                stop_reason="ROUND_TRIP_COMPLETE"
                break

            else:
                validation=self.validator_factory().run_once()
                vstatus=str(validation.get("status") or "")
                row["validation_status"]=vstatus

                if vstatus=="WAITING_FOR_MARKET_SESSION":
                    row["action"]="STOP_OUTSIDE_SESSION"
                    cycle_rows.append(row)
                    stop_reason="WAITING_FOR_MARKET_SESSION"
                    break

                if vstatus!="PASS_ACTUAL_INTRADAY_CANONICAL_READY":
                    row["action"]="NO_ENTRY_NOT_READY"
                    cycle_rows.append(row)
                else:
                    entry=self.entry_factory()
                    if mode=="DRY":
                        plan=entry.build_plan()
                        row["entry_plan_status"]=plan.get("status")
                        row["action"]="DRY_ENTRY_PLAN_ONLY"
                        cycle_rows.append(row)
                    elif state["paper_entry_count"]>=1:
                        row["action"]="ENTRY_LIMIT_REACHED"
                        cycle_rows.append(row)
                    else:
                        result=entry.execute_once(ENTRY_CONFIRMATION)
                        row["entry_status"]=result.get("status")
                        row["paper_entry_order_submitted"]=bool(
                            result.get("paper_order_submitted")
                        )
                        state=self._update_from_entry(state,result)
                        row["action"]="PAPER_ENTRY_ATTEMPT"
                        cycle_rows.append(row)

            if idx<max_cycles:
                self.sleep_fn(interval_seconds)

        result={
            "stage":"BROKER_INTEGRATION_V2_1_26_FULL_ALPACA_PAPER_ROUND_TRIP_CYCLE",
            "status":"PASS_FULL_PAPER_ROUND_TRIP_ORCHESTRATION",
            "mode":mode,
            "cycles_completed":len(cycle_rows),
            "stop_reason":stop_reason,
            "state":state,
            "cycles":cycle_rows,
            "paper_entry_count":state["paper_entry_count"],
            "paper_exit_count":state["paper_exit_count"],
            "maximum_paper_entries_per_cycle":1,
            "maximum_paper_exits_per_cycle":1,
            "live_order_count":state["live_order_count"],
            "automatic_live_trading_enabled":False,
            "completed_at_utc":self._now().isoformat(),
        }
        return self._record(result)
