from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .session_crash_network_restart_recovery_v2_1_30 import (
    SessionCrashNetworkRestartRecoveryV2130,
    RECOVERY_SESSION_CONFIRMATION,
)
from .daily_risk_budget_kill_switch_v2_1_29 import (
    DailyRiskBudgetKillSwitchV2129,
)


DAILY_OPERATION_CONFIRMATION="RUN_ONE_CLICK_DAILY_ALPACA_PAPER_OPERATION"


class OneClickDailyPaperOperationV2131:
    """
    Thin daily-operation launcher over V2.1.30.

    It does NOT call V2.1.21-V2.1.29 individually because V2.1.30 already
    reconnects into the canonical V2.1.29 -> V2.1.28 -> V2.1.26/V2.1.27 chain.

    New responsibilities only:
      - local startup plan in DRY mode;
      - Paper read-only startup recovery reconciliation;
      - bounded wait for Alpaca Paper market clock to become open;
      - delegate the actual guarded session to existing V2.1.30;
      - write a compact daily operation summary.

    No new signal, order, exit, risk, or recovery engine is created.
    """

    def __init__(
        self,
        root,
        *,
        recovery_factory=None,
        risk_factory=None,
        sleep_fn=None,
        now_fn=None,
        config_path=None,
    ):
        self.root=Path(root)
        self.recovery_factory=recovery_factory or (
            lambda:SessionCrashNetworkRestartRecoveryV2130(self.root)
        )
        self.risk_factory=risk_factory or (
            lambda:DailyRiskBudgetKillSwitchV2129(self.root)
        )
        self.sleep_fn=sleep_fn or time.sleep
        self.now_fn=now_fn or (lambda:datetime.now(timezone.utc))

        self.config_path=Path(config_path) if config_path else (
            self.root/"release"/
            "broker_integration_v2_1_31_one_click_daily_paper_operation"/
            "config"/"daily_operation_policy.json"
        )

        self.completed_ledger=(
            self.root/"runtime"/"final_round_trip_ledger_v2_1_27"/
            "completed_round_trips.jsonl"
        )
        self.runtime_dir=(
            self.root/"runtime"/"one_click_daily_paper_operation_v2_1_31"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.operation_ledger=self.runtime_dir/"daily_operation_ledger.jsonl"
        self.latest=self.runtime_dir/"latest_daily_operation.json"

    def _now(self):
        return self.now_fn().astimezone(timezone.utc)

    def _load_policy(self):
        if not self.config_path.exists():
            raise RuntimeError(
                f"DAILY_OPERATION_POLICY_MISSING: {self.config_path}"
            )
        row=json.loads(
            self.config_path.read_text(encoding="utf-8-sig")
        )
        poll=int(row.get("market_wait_poll_seconds",60))
        max_wait=int(row.get("max_market_wait_seconds",64800))
        max_round_trips=int(row.get("max_round_trips",2))
        broker_failure_grace=int(
            row.get("market_wait_broker_failure_grace_seconds",1800)
        )

        if poll<1 or poll>300:
            raise RuntimeError("INVALID_MARKET_WAIT_POLL_SECONDS")
        if max_wait<0 or max_wait>172800:
            raise RuntimeError("INVALID_MAX_MARKET_WAIT_SECONDS")
        if max_round_trips<1 or max_round_trips>3:
            raise RuntimeError("INVALID_MAX_ROUND_TRIPS")
        if broker_failure_grace<0 or broker_failure_grace>7200:
            raise RuntimeError(
                "INVALID_MARKET_WAIT_BROKER_FAILURE_GRACE_SECONDS"
            )

        return {
            **row,
            "market_wait_poll_seconds":poll,
            "max_market_wait_seconds":max_wait,
            "max_round_trips":max_round_trips,
            "market_wait_broker_failure_grace_seconds":
                broker_failure_grace,
        }

    def _append(self,row):
        with self.operation_ledger.open("a",encoding="utf-8") as f:
            f.write(json.dumps(row,sort_keys=True,default=str)+"\n")

    def _write_latest(self,row):
        self.latest.write_text(
            json.dumps(
                row,indent=2,sort_keys=True,default=str
            ),
            encoding="utf-8",
        )
        return row

    def _completed_ids(self):
        if not self.completed_ledger.exists():
            return set()
        out=set()
        for line in self.completed_ledger.read_text(
            encoding="utf-8"
        ).splitlines():
            if not line.strip():
                continue
            try:
                row=json.loads(line)
            except Exception:
                continue
            if (
                row.get("status")
                =="COMPLETED_ALPACA_PAPER_ROUND_TRIP"
                and row.get("round_trip_id")
            ):
                out.add(str(row["round_trip_id"]))
        return out

    def dry_plan(self):
        recovery=self.recovery_factory().local_plan()
        risk=self.risk_factory().evaluate()

        blocked=(
            recovery.get("status","").startswith("BLOCKED_")
            or not risk.get("trading_allowed",False)
        )
        row={
            "status":(
                "BLOCKED_ONE_CLICK_DAILY_DRY_PLAN"
                if blocked
                else "PASS_ONE_CLICK_DAILY_DRY_PLAN"
            ),
            "mode":"DRY",
            "recovery_plan":recovery,
            "risk_status":risk,
            "would_wait_for_market_open":not blocked,
            "would_delegate_to_v2_1_30":not blocked,
            "broker_network_used":False,
            "broker_write_performed":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        }
        self._append(row)
        return self._write_latest(row)

    def _wait_for_market_open(self,recovery,policy):
        started=self._now()
        polls=[]
        outage_started=None
        broker_failure_events=0

        while True:
            snap_result=recovery.acquire_broker_snapshot()
            now=self._now()
            elapsed=max(0.0,(now-started).total_seconds())

            if (
                snap_result.get("status")
                !="PASS_PAPER_BROKER_RECOVERY_SNAPSHOT"
            ):
                broker_failure_events+=1
                if outage_started is None:
                    outage_started=now
                outage_elapsed=max(
                    0.0,(now-outage_started).total_seconds()
                )

                polls.append({
                    "observed_at_utc":now.isoformat(),
                    "broker_read_ok":False,
                    "snapshot_status":snap_result.get("status"),
                    "broker_failure_event":broker_failure_events,
                    "broker_failure_elapsed_seconds":outage_elapsed,
                    "elapsed_seconds":elapsed,
                })

                if elapsed>=policy["max_market_wait_seconds"]:
                    return {
                        "status":"STOPPED_MARKET_WAIT_TIMEOUT",
                        "polls":polls,
                        "broker_failure_events":broker_failure_events,
                        "broker_network_used":True,
                    }

                if (
                    outage_elapsed
                    >=policy[
                        "market_wait_broker_failure_grace_seconds"
                    ]
                ):
                    return {
                        "status":
                            "BLOCKED_MARKET_WAIT_BROKER_UNAVAILABLE",
                        "polls":polls,
                        "last_snapshot_result":snap_result,
                        "broker_failure_events":broker_failure_events,
                        "broker_failure_elapsed_seconds":outage_elapsed,
                        "broker_network_used":True,
                    }

                self.sleep_fn(policy["market_wait_poll_seconds"])
                continue

            outage_started=None
            snap=snap_result["snapshot"]
            clock=snap.get("clock") or {}
            is_open=bool(clock.get("is_open",False))

            polls.append({
                "observed_at_utc":now.isoformat(),
                "broker_read_ok":True,
                "is_open":is_open,
                "next_open":clock.get("next_open"),
                "next_close":clock.get("next_close"),
                "elapsed_seconds":elapsed,
            })

            if is_open:
                return {
                    "status":"PASS_MARKET_OPEN",
                    "polls":polls,
                    "broker_failure_events":broker_failure_events,
                    "broker_network_used":True,
                }

            if elapsed>=policy["max_market_wait_seconds"]:
                return {
                    "status":"STOPPED_MARKET_WAIT_TIMEOUT",
                    "polls":polls,
                    "broker_failure_events":broker_failure_events,
                    "broker_network_used":True,
                }

            self.sleep_fn(policy["market_wait_poll_seconds"])

    def run_paper(self, *, confirmation=""):
        if confirmation!=DAILY_OPERATION_CONFIRMATION:
            return self._write_latest({
                "status":"BLOCKED_DAILY_OPERATION_CONFIRMATION_REQUIRED",
                "required_confirmation":DAILY_OPERATION_CONFIRMATION,
                "mode":"PAPER",
                "paper_orders_submitted_from_stage":0,
                "live_orders_submitted":0,
            })

        policy=self._load_policy()
        recovery=self.recovery_factory()
        risk=self.risk_factory()
        started=self._now()
        baseline_ids=self._completed_ids()

        # First reconcile startup state read-only. Do not wait for market open
        # if startup itself is ambiguous.
        startup=recovery.reconcile()
        if startup.get("status")!="PASS_RECOVERY_RECONCILIATION":
            risk.engage_kill_switch(
                "V2_1_31_STARTUP_RECOVERY_FAIL_CLOSED"
            )
            row={
                "status":"BLOCKED_DAILY_OPERATION_STARTUP_RECOVERY",
                "mode":"PAPER",
                "startup_recovery":startup,
                "kill_switch_engaged":True,
                "paper_orders_submitted_from_stage":0,
                "live_orders_submitted":0,
            }
            self._append(row)
            return self._write_latest(row)

        pre_risk=risk.evaluate()
        if not pre_risk.get("trading_allowed",False):
            row={
                "status":"BLOCKED_DAILY_OPERATION_PRE_RISK",
                "mode":"PAPER",
                "startup_recovery":startup,
                "pre_risk_status":pre_risk,
                "paper_orders_submitted_from_stage":0,
                "live_orders_submitted":0,
            }
            self._append(row)
            return self._write_latest(row)

        wait=self._wait_for_market_open(recovery,policy)
        if wait.get("status")!="PASS_MARKET_OPEN":
            row={
                "status":wait.get("status"),
                "mode":"PAPER",
                "startup_recovery":startup,
                "pre_risk_status":pre_risk,
                "market_wait":wait,
                "paper_orders_submitted_from_stage":0,
                "live_orders_submitted":0,
            }
            self._append(row)
            return self._write_latest(row)

        # Revalidate after overnight wait before any execution delegation.
        post_open_recovery=recovery.reconcile()
        if (
            post_open_recovery.get("status")
            !="PASS_RECOVERY_RECONCILIATION"
        ):
            risk.engage_kill_switch(
                "V2_1_31_2_MARKET_OPEN_RECOVERY_RECHECK_FAIL_CLOSED"
            )
            row={
                "status":"BLOCKED_MARKET_OPEN_RECOVERY_RECHECK",
                "mode":"PAPER",
                "startup_recovery":startup,
                "pre_risk_status":pre_risk,
                "market_wait":wait,
                "post_open_recovery":post_open_recovery,
                "kill_switch_engaged":True,
                "paper_orders_submitted_from_stage":0,
                "live_orders_submitted":0,
            }
            self._append(row)
            return self._write_latest(row)

        post_open_risk=risk.evaluate()
        if not post_open_risk.get("trading_allowed",False):
            row={
                "status":"BLOCKED_MARKET_OPEN_RISK_RECHECK",
                "mode":"PAPER",
                "startup_recovery":startup,
                "pre_risk_status":pre_risk,
                "market_wait":wait,
                "post_open_recovery":post_open_recovery,
                "post_open_risk":post_open_risk,
                "paper_orders_submitted_from_stage":0,
                "live_orders_submitted":0,
            }
            self._append(row)
            return self._write_latest(row)

        # V2.1.30 remains the single operational entry point for recovery +
        # existing daily-risk-guarded Paper trading.
        delegated=recovery.recover_and_resume(
            mode="PAPER",
            confirmation=RECOVERY_SESSION_CONFIRMATION,
            max_round_trips=policy["max_round_trips"],
            interval_seconds=policy["session_interval_seconds"],
        )

        post_risk=risk.evaluate()
        final_ids=self._completed_ids()
        new_ids=sorted(final_ids-baseline_ids)
        ended=self._now()

        row={
            "stage":
                "BROKER_INTEGRATION_V2_1_31_ONE_CLICK_DAILY_PAPER_OPERATION",
            "status":"PASS_ONE_CLICK_DAILY_PAPER_OPERATION",
            "mode":"PAPER",
            "started_at_utc":started.isoformat(),
            "ended_at_utc":ended.isoformat(),
            "duration_seconds":
                max(0.0,(ended-started).total_seconds()),
            "startup_recovery_status":startup.get("status"),
            "startup_recovery_action":
                startup.get("recovery_action"),
            "market_wait_status":wait.get("status"),
            "market_wait_polls":len(wait.get("polls",[])),
            "market_wait_broker_failure_events":
                wait.get("broker_failure_events",0),
            "post_open_recovery_status":
                post_open_recovery.get("status"),
            "post_open_recovery_action":
                post_open_recovery.get("recovery_action"),
            "post_open_risk_status":post_open_risk,
            "delegated_v2_1_30_status":delegated.get("status"),
            "delegated_stop_reason":
                delegated.get("delegated_stop_reason"),
            "post_risk_status":post_risk,
            "new_completed_round_trip_ids":new_ids,
            "new_completed_round_trip_count":len(new_ids),
            "v2_1_30_operational_entry_reused":True,
            "v2_1_29_risk_reused":True,
            "new_signal_engine_created":False,
            "new_order_engine_created":False,
            "new_recovery_engine_created":False,
            "paper_orders_submitted_from_v2_1_31":0,
            "live_orders_submitted":0,
            "live_trading_enabled":False,
        }
        self._append(row)
        return self._write_latest(row)
