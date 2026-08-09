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
    CONFIRMATION_PHRASE,
)
from .alpaca_paper_order_position_lifecycle_bridge_v2_1_23 import (
    AlpacaPaperOrderPositionLifecycleBridgeV2123,
)


SESSION_CONFIRMATION="RUN_ALPACA_PAPER_SESSION"


class PaperIntradayAutonomousSessionControllerV2124:
    """
    Bounded session orchestrator over existing V2.1.21 -> V2.1.22 -> V2.1.23.

    No new market-data, signal, broker adapter, order request, or exit strategy
    engine is created here.

    Dry mode:
      - V2.1.21 validation only
      - V2.1.22 dry plan only
      - V2.1.23 dry plan only
      - no broker network/order submission from this controller

    Paper mode:
      - explicit SESSION_CONFIRMATION required
      - V2.1.22 existing explicit Paper confirmation reused
      - existing manual PAPER_ONLY arm token still enforced by V2.1.22 preflight
      - max one Paper entry submission for the session
      - V2.1.23 lifecycle remains read-only
      - no exit order submission
      - live trading remains disabled
    """

    def __init__(
        self,
        root,
        *,
        validator_factory=None,
        execution_factory=None,
        lifecycle_factory=None,
        sleep_fn=None,
        now_fn=None,
    ):
        self.root=Path(root)
        self.validator_factory=validator_factory or (
            lambda:self._default_validator()
        )
        self.execution_factory=execution_factory or (
            lambda:AlpacaPaperBoundedExecutionBridgeV2122(self.root)
        )
        self.lifecycle_factory=lifecycle_factory or (
            lambda:AlpacaPaperOrderPositionLifecycleBridgeV2123(self.root)
        )
        self.sleep_fn=sleep_fn or time.sleep
        self.now_fn=now_fn or (lambda:datetime.now(timezone.utc))

        self.runtime_dir=(
            self.root/"runtime"/"paper_intraday_autonomous_session_v2_1_24"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.ledger=self.runtime_dir/"session_ledger.jsonl"
        self.latest=self.runtime_dir/"latest_session.json"

    def _default_validator(self):
        return ActualIntradayCanonicalEndToEndValidatorV2121(
            self.root
        )

    def _write(self,row):
        self.latest.write_text(
            json.dumps(
                row,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )
        with self.ledger.open("a",encoding="utf-8") as f:
            f.write(
                json.dumps(
                    row,
                    sort_keys=True,
                    ensure_ascii=False,
                    default=str,
                )+"\n"
            )
        return row

    def run(
        self,
        *,
        mode="DRY",
        session_confirmation="",
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

        if mode=="PAPER" and session_confirmation!=SESSION_CONFIRMATION:
            return self._write({
                "status":"BLOCKED_SESSION_CONFIRMATION_REQUIRED",
                "required_confirmation":SESSION_CONFIRMATION,
                "mode":mode,
                "cycles_completed":0,
                "paper_orders_submitted":0,
                "exit_orders_submitted":0,
                "live_orders_submitted":0,
            })

        session_id=(
            "v2124-"
            +self.now_fn().astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        )
        cycle_rows=[]
        paper_orders=0
        lifecycle_monitors=0
        stop_reason="MAX_CYCLES"

        for idx in range(1,max_cycles+1):
            validation=self.validator_factory().run_once()
            status=str(validation.get("status") or "")

            cycle={
                "cycle":idx,
                "validation_status":status,
                "paper_submission_attempted":False,
                "paper_order_submitted":False,
                "lifecycle_monitored":False,
            }

            if status=="WAITING_FOR_MARKET_SESSION":
                cycle["action"]="STOP_OUTSIDE_SESSION"
                cycle_rows.append(cycle)
                stop_reason="WAITING_FOR_MARKET_SESSION"
                break

            if status in {
                "BLOCKED_BY_SESSION_FRESHNESS",
                "BLOCKED_BY_CANONICAL_PROVENANCE",
            }:
                cycle["action"]="NO_ORDER_BLOCKED"
                cycle_rows.append(cycle)

            elif status=="PASS_FRESH_NO_ELIGIBLE_SIGNAL":
                cycle["action"]="NO_ORDER_NO_SIGNAL"
                cycle_rows.append(cycle)

            elif status=="PASS_ACTUAL_INTRADAY_CANONICAL_NOT_READY":
                cycle["action"]="NO_ORDER_NOT_READY"
                cycle_rows.append(cycle)

            elif status=="PASS_ACTUAL_INTRADAY_CANONICAL_READY":
                bridge=self.execution_factory()

                if mode=="DRY":
                    plan=bridge.build_plan()
                    cycle["paper_plan_status"]=plan.get("status")
                    cycle["action"]="DRY_PLAN_ONLY"
                    cycle_rows.append(cycle)

                elif paper_orders>=1:
                    cycle["action"]="SESSION_PAPER_ORDER_LIMIT_REACHED"
                    cycle_rows.append(cycle)

                else:
                    cycle["paper_submission_attempted"]=True
                    result=bridge.execute_once(CONFIRMATION_PHRASE)
                    cycle["paper_submission_status"]=result.get("status")
                    submitted=result.get("paper_order_submitted") is True
                    cycle["paper_order_submitted"]=submitted

                    if submitted:
                        paper_orders+=1
                        lifecycle=self.lifecycle_factory()
                        life=lifecycle.monitor_once(
                            interval_seconds=5,
                            max_cycles=lifecycle_cycles,
                        )
                        lifecycle_monitors+=1
                        cycle["lifecycle_monitored"]=True
                        cycle["lifecycle_status"]=life.get("status")
                        cycle["position_lifecycle_state"]=(
                            life.get("position_lifecycle_state")
                        )
                        cycle["exit_order_submitted"]=False
                        cycle["action"]="PAPER_ENTRY_AND_READ_ONLY_LIFECYCLE"
                    else:
                        cycle["action"]="PAPER_SUBMISSION_BLOCKED"

                    cycle_rows.append(cycle)

            else:
                cycle["action"]="UNKNOWN_VALIDATION_STATUS_NO_ORDER"
                cycle_rows.append(cycle)

            if idx<max_cycles:
                self.sleep_fn(interval_seconds)

        result={
            "stage":
                "BROKER_INTEGRATION_V2_1_24_PAPER_INTRADAY_AUTONOMOUS_SESSION_CONTROLLER",
            "status":"PASS_BOUNDED_PAPER_INTRADAY_SESSION",
            "session_id":session_id,
            "mode":mode,
            "cycles_completed":len(cycle_rows),
            "max_cycles":max_cycles,
            "interval_seconds":interval_seconds,
            "stop_reason":stop_reason,
            "cycles":cycle_rows,
            "paper_orders_submitted":paper_orders,
            "maximum_paper_orders_per_session":1,
            "lifecycle_monitors_run":lifecycle_monitors,
            "exit_orders_submitted":0,
            "live_orders_submitted":0,
            "automatic_exit_write_enabled":False,
            "live_trading_enabled":False,
            "completed_at_utc":
                self.now_fn().astimezone(timezone.utc).isoformat(),
        }
        return self._write(result)
