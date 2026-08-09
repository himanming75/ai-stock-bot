from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from paper_order_lifecycle.client import AlpacaPaperReadClient

from .daily_risk_budget_kill_switch_v2_1_29 import (
    DailyRiskBudgetKillSwitchV2129,
    DAILY_RISK_SESSION_CONFIRMATION,
)
from .continuous_bounded_paper_session_rollover_v2_1_28 import (
    ContinuousBoundedPaperSessionRolloverV2128,
)
from .final_exit_fill_reconciliation_round_trip_ledger_v2_1_27 import (
    FinalExitFillReconciliationRoundTripLedgerV2127,
)


RECOVERY_SESSION_CONFIRMATION="RUN_RECOVERY_GUARDED_ALPACA_PAPER_SESSION"


class SessionCrashNetworkRestartRecoveryV2130:
    """
    Read-only recovery supervisor over existing V2.1.26-V2.1.29.

    It does NOT create a new trading state machine.

    Startup workflow:
      1. load durable local state;
      2. acquire bounded-retry Alpaca Paper READ snapshot;
      3. reconcile local state vs broker orders/positions;
      4. classify the safe continuation action;
      5. fail closed on ambiguity;
      6. only after a PASS recovery classification, delegate back to the
         existing V2.1.29 daily-risk-guarded session.

    No broker write is performed by the recovery inspection itself.
    """

    def __init__(
        self,
        root,
        *,
        client_factory=None,
        risk_factory=None,
        rollover_factory=None,
        finalizer_factory=None,
        sleep_fn=None,
        now_fn=None,
        config_path=None,
    ):
        self.root=Path(root)
        self.client_factory=client_factory or AlpacaPaperReadClient
        self.risk_factory=risk_factory or (
            lambda:DailyRiskBudgetKillSwitchV2129(self.root)
        )
        self.rollover_factory=rollover_factory or (
            lambda:ContinuousBoundedPaperSessionRolloverV2128(self.root)
        )
        self.finalizer_factory=finalizer_factory or (
            lambda:FinalExitFillReconciliationRoundTripLedgerV2127(self.root)
        )
        self.sleep_fn=sleep_fn or time.sleep
        self.now_fn=now_fn or (lambda:datetime.now(timezone.utc))

        self.config_path=Path(config_path) if config_path else (
            self.root/"release"/
            "broker_integration_v2_1_30_session_crash_network_restart_recovery"/
            "config"/"recovery_policy.json"
        )

        self.cycle_state_path=(
            self.root/"runtime"/"full_alpaca_paper_round_trip_v2_1_26"/
            "cycle_state.json"
        )
        self.exit_ledger_path=(
            self.root/"runtime"/"alpaca_paper_exit_recovery_v2_1_25"/
            "exit_ledger.jsonl"
        )

        self.runtime_dir=(
            self.root/"runtime"/"session_crash_network_restart_recovery_v2_1_30"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.recovery_ledger=self.runtime_dir/"recovery_ledger.jsonl"
        self.latest=self.runtime_dir/"latest_recovery.json"

    def _now(self):
        return self.now_fn().astimezone(timezone.utc)

    def _load_policy(self):
        if not self.config_path.exists():
            raise RuntimeError(f"RECOVERY_POLICY_MISSING: {self.config_path}")
        row=json.loads(self.config_path.read_text(encoding="utf-8-sig"))
        attempts=int(row.get("broker_read_max_attempts",3))
        delay=float(row.get("broker_read_retry_seconds",2))
        if attempts<1 or attempts>10:
            raise RuntimeError("INVALID_BROKER_READ_MAX_ATTEMPTS")
        if delay<0 or delay>60:
            raise RuntimeError("INVALID_BROKER_READ_RETRY_SECONDS")
        return {
            **row,
            "broker_read_max_attempts":attempts,
            "broker_read_retry_seconds":delay,
        }

    @staticmethod
    def _read_json(path):
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _state(self):
        if not self.cycle_state_path.exists():
            return None
        try:
            return self._read_json(self.cycle_state_path)
        except Exception as exc:
            return {
                "_invalid":True,
                "_error":f"{type(exc).__name__}: {exc}",
            }

    def _latest_submitted_exit(self):
        if not self.exit_ledger_path.exists():
            return None
        latest=None
        for line in self.exit_ledger_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row=json.loads(line)
            except Exception:
                continue
            if row.get("paper_exit_order_submitted") is True:
                latest=row
        return latest

    def _write_latest(self,row):
        self.latest.write_text(
            json.dumps(row,indent=2,sort_keys=True,default=str),
            encoding="utf-8",
        )
        return row

    def _append(self,row):
        with self.recovery_ledger.open("a",encoding="utf-8") as f:
            f.write(json.dumps(row,sort_keys=True,default=str)+"\n")

    def local_plan(self):
        state=self._state()

        if state is None:
            return self._write_latest({
                "status":"PASS_LOCAL_RECOVERY_PLAN",
                "recovery_action":"IDLE_START",
                "reason":"NO_V2_1_26_STATE",
                "broker_network_used":False,
                "broker_write_performed":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            })

        if state.get("_invalid"):
            return self._write_latest({
                "status":"BLOCKED_INVALID_LOCAL_CYCLE_STATE",
                "recovery_action":"FAIL_CLOSED",
                "error":state.get("_error"),
                "broker_network_used":False,
                "broker_write_performed":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            })

        phase=str(state.get("phase") or "")
        if state.get("round_trip_complete"):
            action="ROLLOVER_REQUIRED"
        elif state.get("exit_submitted"):
            action="FINAL_EXIT_RECONCILIATION_REQUIRED"
        elif state.get("entry_submitted"):
            action="RESUME_ENTRY_POSITION_LIFECYCLE"
        elif phase in {"IDLE",""}:
            action="IDLE_START"
        else:
            action="FAIL_CLOSED"

        status=(
            "PASS_LOCAL_RECOVERY_PLAN"
            if action!="FAIL_CLOSED"
            else "BLOCKED_UNKNOWN_LOCAL_PHASE"
        )
        return self._write_latest({
            "status":status,
            "recovery_action":action,
            "phase":phase,
            "state":state,
            "broker_network_used":False,
            "broker_write_performed":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        })

    def _read_broker_snapshot_once(self):
        client=self.client_factory()
        positions=client.get_positions()
        account=client.get_account()
        clock=client.get_clock()

        state=self._state()
        entry_client_order_id=None
        if state and not state.get("_invalid"):
            entry_client_order_id=state.get("entry_client_order_id")

        entry_order=None
        if entry_client_order_id:
            entry_order=client.get_order_by_client_id(entry_client_order_id)

        latest_exit=self._latest_submitted_exit()
        exit_client_order_id=None
        if latest_exit:
            exit_client_order_id=(
                (latest_exit.get("exit_order") or {}).get("client_order_id")
            )

        exit_order=None
        if exit_client_order_id:
            exit_order=client.get_order_by_client_id(exit_client_order_id)

        return {
            "observed_at_utc":self._now().isoformat(),
            "positions":positions,
            "position_symbols":sorted(
                str(p.get("symbol") or "").upper()
                for p in positions
                if p.get("symbol")
            ),
            "account":{
                "status":account.get("status"),
                "equity":account.get("equity"),
                "cash":account.get("cash"),
                "buying_power":account.get("buying_power"),
            },
            "clock":{
                "is_open":bool(clock.get("is_open",False)),
                "timestamp":clock.get("timestamp"),
                "next_open":clock.get("next_open"),
                "next_close":clock.get("next_close"),
            },
            "entry_order":entry_order,
            "exit_order":exit_order,
            "actual_external_network_used":True,
            "actual_broker_read_performed":True,
            "actual_broker_write_performed":False,
            "actual_order_submission_performed":False,
        }

    def acquire_broker_snapshot(self):
        policy=self._load_policy()
        errors=[]

        for attempt in range(1,policy["broker_read_max_attempts"]+1):
            try:
                snap=self._read_broker_snapshot_once()
                snap["attempt"]=attempt
                snap["retry_errors"]=errors
                return {
                    "status":"PASS_PAPER_BROKER_RECOVERY_SNAPSHOT",
                    "snapshot":snap,
                    "attempts_used":attempt,
                    "broker_network_used":True,
                    "broker_write_performed":False,
                    "paper_orders_submitted":0,
                    "live_orders_submitted":0,
                }
            except Exception as exc:
                errors.append({
                    "attempt":attempt,
                    "error_type":type(exc).__name__,
                    "error":str(exc),
                })
                if attempt<policy["broker_read_max_attempts"]:
                    self.sleep_fn(policy["broker_read_retry_seconds"])

        return {
            "status":"BLOCKED_BROKER_READ_RETRIES_EXHAUSTED",
            "recovery_action":"FAIL_CLOSED",
            "errors":errors,
            "attempts_used":len(errors),
            "broker_network_used":True,
            "broker_write_performed":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        }

    @staticmethod
    def _order_status(order):
        return str((order or {}).get("status") or "").lower()

    def reconcile(self):
        local=self.local_plan()
        if local["status"].startswith("BLOCKED_"):
            result={
                **local,
                "status":"BLOCKED_RECOVERY_LOCAL_STATE",
            }
            self._append(result)
            return self._write_latest(result)

        broker=self.acquire_broker_snapshot()
        if broker["status"]!="PASS_PAPER_BROKER_RECOVERY_SNAPSHOT":
            result={
                **broker,
                "status":"BLOCKED_RECOVERY_BROKER_UNAVAILABLE",
            }
            self._append(result)
            return self._write_latest(result)

        snap=broker["snapshot"]
        state=self._state()
        action=local["recovery_action"]
        symbols=set(snap["position_symbols"])
        symbol=(
            str((state or {}).get("symbol") or "").upper().strip()
            if state else ""
        )
        entry_status=self._order_status(snap.get("entry_order"))
        exit_status=self._order_status(snap.get("exit_order"))
        broker_has_symbol=bool(symbol and symbol in symbols)

        reasons=[]
        safe_action=action

        if action=="IDLE_START":
            # No local active cycle must not silently coexist with a broker
            # position. Fail closed rather than inventing ownership.
            if symbols:
                reasons.append("BROKER_POSITION_EXISTS_WITH_NO_ACTIVE_LOCAL_CYCLE")

        elif action=="RESUME_ENTRY_POSITION_LIFECYCLE":
            if not symbol:
                reasons.append("LOCAL_ACTIVE_ENTRY_SYMBOL_MISSING")
            if snap.get("entry_order") is None:
                reasons.append("ENTRY_ORDER_NOT_FOUND_AT_BROKER")
            elif entry_status in {"canceled","cancelled","rejected","expired"}:
                reasons.append("ENTRY_ORDER_TERMINAL_NONFILLED")
            elif entry_status=="filled" and not broker_has_symbol:
                reasons.append("ENTRY_FILLED_BUT_POSITION_MISSING")
            safe_action="RESUME_V2_1_26_RECOVERY_FIRST"

        elif action=="FINAL_EXIT_RECONCILIATION_REQUIRED":
            if snap.get("exit_order") is None:
                reasons.append("EXIT_ORDER_NOT_FOUND_AT_BROKER")
            elif exit_status=="filled" and broker_has_symbol:
                reasons.append("EXIT_FILLED_BUT_POSITION_REMAINS")
            safe_action="RUN_V2_1_27_FINAL_RECONCILIATION"

        elif action=="ROLLOVER_REQUIRED":
            rollover=self.rollover_factory().build_rollover_plan()
            if rollover.get("status")!="READY_FOR_SAFE_CYCLE_ROLLOVER":
                reasons.append(
                    "V2_1_28_ROLLOVER_PROOF_NOT_READY:"
                    +str(rollover.get("status"))
                )
            if broker_has_symbol:
                reasons.append("POSITION_REMAINS_AFTER_LOCAL_COMPLETION")
            safe_action="RUN_V2_1_28_SAFE_ROLLOVER"

        if reasons:
            result={
                "status":"BLOCKED_RECOVERY_STATE_MISMATCH",
                "recovery_action":"FAIL_CLOSED",
                "mismatch_reasons":reasons,
                "local_plan":local,
                "broker_snapshot":snap,
                "broker_network_used":True,
                "broker_write_performed":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            }
            self._append(result)
            return self._write_latest(result)

        result={
            "status":"PASS_RECOVERY_RECONCILIATION",
            "recovery_action":safe_action,
            "local_plan":local,
            "broker_snapshot":snap,
            "broker_network_used":True,
            "broker_write_performed":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        }
        self._append(result)
        return self._write_latest(result)

    def recover_and_resume(
        self,
        *,
        mode="DRY",
        confirmation="",
        max_round_trips=2,
        interval_seconds=30,
    ):
        mode=str(mode or "DRY").upper()
        if mode not in {"DRY","PAPER"}:
            raise ValueError("mode must be DRY or PAPER")

        if (
            mode=="PAPER"
            and confirmation!=RECOVERY_SESSION_CONFIRMATION
        ):
            return self._write_latest({
                "status":"BLOCKED_RECOVERY_SESSION_CONFIRMATION_REQUIRED",
                "required_confirmation":RECOVERY_SESSION_CONFIRMATION,
                "mode":mode,
                "paper_orders_submitted_from_stage":0,
                "live_orders_submitted":0,
            })

        rec=self.reconcile()
        if rec["status"]!="PASS_RECOVERY_RECONCILIATION":
            # Persistent network failure or state mismatch must stop new
            # trading. Reuse V2.1.29 kill switch rather than adding another.
            if mode=="PAPER":
                self.risk_factory().engage_kill_switch(
                    "V2_1_30_RECOVERY_FAIL_CLOSED"
                )
            return self._write_latest({
                **rec,
                "status":"BLOCKED_RECOVERY_RESUME",
                "kill_switch_engaged":mode=="PAPER",
            })

        action=rec["recovery_action"]

        if mode=="DRY":
            return self._write_latest({
                "status":"PASS_RECOVERY_DRY_PLAN",
                "mode":"DRY",
                "recovery_action":action,
                "broker_network_used":True,
                "broker_write_performed":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            })

        # For a completed state, perform the existing verified local rollover
        # first. No order is submitted by rollover.
        if action=="RUN_V2_1_28_SAFE_ROLLOVER":
            rolled=self.rollover_factory().rollover_once()
            if rolled.get("status")!="PASS_SAFE_CYCLE_ROLLOVER":
                self.risk_factory().engage_kill_switch(
                    "V2_1_30_ROLLOVER_FAILED"
                )
                return self._write_latest({
                    "status":"BLOCKED_RECOVERY_ROLLOVER_FAILED",
                    "rollover_result":rolled,
                    "kill_switch_engaged":True,
                })

        # If exit submission exists, finish its read-only reconciliation before
        # allowing another daily-risk-guarded session.
        if action=="RUN_V2_1_27_FINAL_RECONCILIATION":
            finalized=self.finalizer_factory().reconcile(
                interval_seconds=5,
                max_cycles=12,
            )
            if finalized.get("status") not in {
                "PASS_FINAL_EXIT_FILL_RECONCILIATION",
                "ROUND_TRIP_ALREADY_COMPLETED_NO_DUPLICATE",
            }:
                return self._write_latest({
                    "status":"WAITING_OR_BLOCKED_FINAL_RECONCILIATION",
                    "finalizer_result":finalized,
                    "paper_orders_submitted_from_stage":0,
                    "live_orders_submitted":0,
                })

        # Existing V2.1.29 remains the only daily trading supervisor.
        delegated=self.risk_factory().run_guarded_session(
            mode="PAPER",
            confirmation=DAILY_RISK_SESSION_CONFIRMATION,
            max_supervisor_round_trips=max_round_trips,
            interval_seconds=interval_seconds,
        )

        result={
            "status":"PASS_RECOVERY_RESUMED_EXISTING_V2_1_29",
            "mode":"PAPER",
            "recovery_action":action,
            "delegated_v2_1_29_status":delegated.get("status"),
            "delegated_stop_reason":delegated.get("stop_reason"),
            "new_trading_engine_created":False,
            "live_orders_submitted":0,
            "live_trading_enabled":False,
        }
        self._append(result)
        return self._write_latest(result)
