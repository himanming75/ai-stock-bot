from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

from .continuous_bounded_paper_session_rollover_v2_1_28 import (
    ContinuousBoundedPaperSessionRolloverV2128,
    CONTINUOUS_SESSION_CONFIRMATION,
)


DAILY_RISK_SESSION_CONFIRMATION="RUN_DAILY_RISK_GUARDED_ALPACA_PAPER_SESSION"


class DailyRiskBudgetKillSwitchV2129:
    """
    Daily risk wrapper around existing V2.1.28.

    No signal, entry, exit, broker, lifecycle, or reconciliation engine is
    implemented here.

    V2.1.29 intentionally invokes V2.1.28 with max_completed_round_trips=1,
    then recalculates the daily risk budget from the immutable V2.1.27
    completed-round-trip ledger before allowing another round-trip.

    Risk accounting is based on V2.1.27:
      FILL_BASED_GROSS_PNL_BEFORE_FEES

    It is therefore a conservative operational guard, not a broker tax-lot
    realized-P&L statement.
    """

    def __init__(
        self,
        root,
        *,
        session_factory=None,
        now_fn=None,
        sleep_fn=None,
        config_path=None,
    ):
        self.root=Path(root)
        self.session_factory=session_factory or (
            lambda:ContinuousBoundedPaperSessionRolloverV2128(self.root)
        )
        self.now_fn=now_fn or (lambda:datetime.now(timezone.utc))
        self.sleep_fn=sleep_fn or time.sleep

        self.config_path=Path(config_path) if config_path else (
            self.root/"release"/
            "broker_integration_v2_1_29_daily_risk_budget_kill_switch"/
            "config"/"daily_risk_policy.json"
        )

        self.completed_ledger=(
            self.root/"runtime"/"final_round_trip_ledger_v2_1_27"/
            "completed_round_trips.jsonl"
        )

        self.runtime_dir=(
            self.root/"runtime"/"daily_risk_budget_kill_switch_v2_1_29"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.kill_switch_path=self.runtime_dir/"KILL_SWITCH.json"
        self.risk_ledger=self.runtime_dir/"risk_ledger.jsonl"
        self.latest=self.runtime_dir/"latest_risk_status.json"

        self.market_tz=ZoneInfo("America/New_York")

    def _now(self):
        return self.now_fn().astimezone(timezone.utc)

    def _load_policy(self):
        if not self.config_path.exists():
            raise RuntimeError(
                f"DAILY_RISK_POLICY_MISSING: {self.config_path}"
            )
        p=json.loads(self.config_path.read_text(encoding="utf-8-sig"))
        required=(
            "max_completed_round_trips_per_day",
            "max_daily_gross_loss_usd",
            "max_consecutive_losses",
        )
        for key in required:
            if key not in p:
                raise RuntimeError(f"DAILY_RISK_POLICY_FIELD_MISSING: {key}")

        max_trades=int(p["max_completed_round_trips_per_day"])
        max_loss=Decimal(str(p["max_daily_gross_loss_usd"]))
        max_consecutive=int(p["max_consecutive_losses"])

        if not (1 <= max_trades <= 10):
            raise RuntimeError("INVALID_MAX_COMPLETED_ROUND_TRIPS_PER_DAY")
        if max_loss <= 0:
            raise RuntimeError("INVALID_MAX_DAILY_GROSS_LOSS_USD")
        if not (1 <= max_consecutive <= 10):
            raise RuntimeError("INVALID_MAX_CONSECUTIVE_LOSSES")

        return {
            **p,
            "max_completed_round_trips_per_day":max_trades,
            "max_daily_gross_loss_usd":str(max_loss),
            "max_consecutive_losses":max_consecutive,
        }

    def _write_latest(self,row):
        self.latest.write_text(
            json.dumps(row,indent=2,sort_keys=True,default=str),
            encoding="utf-8",
        )
        return row

    def _append(self,row):
        with self.risk_ledger.open("a",encoding="utf-8") as f:
            f.write(json.dumps(row,sort_keys=True,default=str)+"\n")

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

    @staticmethod
    def _decimal(value):
        try:
            return Decimal(str(value))
        except (InvalidOperation,ValueError,TypeError):
            raise RuntimeError("INVALID_COMPLETED_LEDGER_PNL")

    def _row_market_date(self,row):
        value=row.get("completed_at_utc")
        if not value:
            return None
        try:
            dt=datetime.fromisoformat(
                str(value).replace("Z","+00:00")
            )
        except ValueError:
            return None
        if dt.tzinfo is None:
            dt=dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(self.market_tz).date().isoformat()

    def _today_market_date(self):
        return self._now().astimezone(self.market_tz).date().isoformat()

    def _today_rows(self):
        today=self._today_market_date()
        return [
            r for r in self._completed_rows()
            if self._row_market_date(r)==today
        ]

    def _manual_kill_state(self):
        if not self.kill_switch_path.exists():
            return {
                "engaged":False,
                "reason":None,
                "engaged_at_utc":None,
            }
        try:
            row=json.loads(
                self.kill_switch_path.read_text(encoding="utf-8-sig")
            )
        except Exception:
            return {
                "engaged":True,
                "reason":"KILL_SWITCH_FILE_INVALID_FAIL_CLOSED",
                "engaged_at_utc":None,
            }
        return {
            "engaged":bool(row.get("engaged",True)),
            "reason":row.get("reason"),
            "engaged_at_utc":row.get("engaged_at_utc"),
        }

    def engage_kill_switch(self,reason="MANUAL_KILL_SWITCH"):
        row={
            "engaged":True,
            "reason":str(reason or "MANUAL_KILL_SWITCH"),
            "engaged_at_utc":self._now().isoformat(),
            "stage":"V2.1.29",
        }
        self.kill_switch_path.write_text(
            json.dumps(row,indent=2,sort_keys=True),
            encoding="utf-8",
        )
        return self._write_latest({
            "status":"PASS_KILL_SWITCH_ENGAGED",
            "kill_switch":row,
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        })

    def clear_kill_switch(self):
        if self.kill_switch_path.exists():
            self.kill_switch_path.unlink()
        return self._write_latest({
            "status":"PASS_KILL_SWITCH_CLEARED",
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        })

    @staticmethod
    def _consecutive_losses(rows):
        count=0
        for row in reversed(rows):
            pnl=DailyRiskBudgetKillSwitchV2129._decimal(
                row.get("gross_pnl_from_fills")
            )
            if pnl < 0:
                count+=1
            else:
                break
        return count

    def evaluate(self):
        policy=self._load_policy()
        manual=self._manual_kill_state()
        rows=self._today_rows()

        pnls=[
            self._decimal(r.get("gross_pnl_from_fills"))
            for r in rows
        ]
        total_pnl=sum(pnls,Decimal("0"))
        gross_loss=max(Decimal("0"),-total_pnl)
        trades=len(rows)
        consecutive_losses=self._consecutive_losses(rows)

        reasons=[]
        if manual["engaged"]:
            reasons.append(
                manual["reason"] or "MANUAL_KILL_SWITCH"
            )
        if trades >= policy["max_completed_round_trips_per_day"]:
            reasons.append("MAX_DAILY_ROUND_TRIPS_REACHED")
        if gross_loss >= Decimal(policy["max_daily_gross_loss_usd"]):
            reasons.append("MAX_DAILY_GROSS_LOSS_REACHED")
        if consecutive_losses >= policy["max_consecutive_losses"]:
            reasons.append("MAX_CONSECUTIVE_LOSSES_REACHED")

        allowed=not reasons
        remaining_trades=max(
            0,
            policy["max_completed_round_trips_per_day"]-trades,
        )
        remaining_loss=max(
            Decimal("0"),
            Decimal(policy["max_daily_gross_loss_usd"])-gross_loss,
        )

        row={
            "status":(
                "PASS_DAILY_RISK_BUDGET_ALLOW"
                if allowed
                else "BLOCKED_BY_DAILY_RISK_OR_KILL_SWITCH"
            ),
            "market_date":self._today_market_date(),
            "trading_allowed":allowed,
            "block_reasons":reasons,
            "policy":policy,
            "completed_round_trips_today":trades,
            "daily_fill_based_gross_pnl_before_fees":str(total_pnl),
            "daily_gross_loss_budget_used_usd":str(gross_loss),
            "consecutive_losses":consecutive_losses,
            "remaining_round_trips_today":remaining_trades,
            "remaining_daily_gross_loss_budget_usd":str(remaining_loss),
            "manual_kill_switch":manual,
            "pnl_semantics":"V2.1.27_FILL_BASED_GROSS_PNL_BEFORE_FEES",
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        }
        self._append(row)
        return self._write_latest(row)

    def run_guarded_session(
        self,
        *,
        mode="DRY",
        confirmation="",
        max_supervisor_round_trips=2,
        interval_seconds=30,
    ):
        mode=str(mode or "DRY").upper()
        if mode not in {"DRY","PAPER"}:
            raise ValueError("mode must be DRY or PAPER")
        if max_supervisor_round_trips<1 or max_supervisor_round_trips>3:
            raise ValueError(
                "max_supervisor_round_trips must be between 1 and 3"
            )
        if interval_seconds<1:
            raise ValueError("interval_seconds must be >= 1")

        if (
            mode=="PAPER"
            and confirmation!=DAILY_RISK_SESSION_CONFIRMATION
        ):
            return self._write_latest({
                "status":"BLOCKED_DAILY_RISK_SESSION_CONFIRMATION_REQUIRED",
                "required_confirmation":DAILY_RISK_SESSION_CONFIRMATION,
                "mode":mode,
                "paper_orders_submitted_from_stage":0,
                "live_orders_submitted":0,
            })

        session_rows=[]
        stop_reason="MAX_SUPERVISOR_ROUND_TRIPS_REACHED"

        for attempt in range(1,max_supervisor_round_trips+1):
            before=self.evaluate()
            session_rows.append({
                "attempt":attempt,
                "phase":"PRE_RISK_CHECK",
                "risk_status":before["status"],
                "trading_allowed":before["trading_allowed"],
                "block_reasons":before["block_reasons"],
            })

            if not before["trading_allowed"]:
                stop_reason="DAILY_RISK_OR_KILL_SWITCH_BLOCK"
                break

            # Exactly one completed round-trip max per delegated V2.1.28 call.
            # This guarantees a fresh V2.1.29 risk evaluation before another.
            delegated=self.session_factory().run(
                mode=mode,
                confirmation=(
                    CONTINUOUS_SESSION_CONFIRMATION
                    if mode=="PAPER"
                    else ""
                ),
                max_completed_round_trips=1,
                max_supervisor_cycles=40 if mode=="PAPER" else 3,
                interval_seconds=interval_seconds,
            )
            session_rows.append({
                "attempt":attempt,
                "phase":"DELEGATED_V2_1_28",
                "result_status":delegated.get("status"),
                "stop_reason":delegated.get("stop_reason"),
                "completed_round_trips_this_session":
                    delegated.get("completed_round_trips_this_session",0),
                "new_completed_round_trip_ids":
                    delegated.get("new_completed_round_trip_ids",[]),
            })

            if delegated.get("stop_reason")=="WAITING_FOR_MARKET_SESSION":
                stop_reason="WAITING_FOR_MARKET_SESSION"
                break

            if delegated.get("status")!="PASS_CONTINUOUS_BOUNDED_PAPER_SESSION":
                # Fail closed on abnormal orchestration result.
                self.engage_kill_switch(
                    "ABNORMAL_V2_1_28_SESSION_STATUS"
                )
                stop_reason="ABNORMAL_SESSION_STATUS_KILL_SWITCH"
                break

            after=self.evaluate()
            session_rows.append({
                "attempt":attempt,
                "phase":"POST_RISK_CHECK",
                "risk_status":after["status"],
                "trading_allowed":after["trading_allowed"],
                "block_reasons":after["block_reasons"],
            })

            if not after["trading_allowed"]:
                stop_reason="POST_TRADE_DAILY_RISK_BLOCK"
                break

            # In DRY mode no completed trade is expected. Do not loop
            # unnecessarily after a dry delegated pass.
            if (
                mode=="DRY"
                and delegated.get(
                    "completed_round_trips_this_session",0
                )==0
            ):
                stop_reason="DRY_NO_COMPLETED_ROUND_TRIP"
                break

            if attempt<max_supervisor_round_trips:
                self.sleep_fn(interval_seconds)

        final_risk=self.evaluate()
        result={
            "stage":"BROKER_INTEGRATION_V2_1_29_DAILY_RISK_BUDGET_KILL_SWITCH",
            "status":"PASS_DAILY_RISK_GUARDED_SESSION",
            "mode":mode,
            "stop_reason":stop_reason,
            "session_rows":session_rows,
            "final_risk_status":final_risk,
            "v2_1_28_reused":True,
            "delegated_max_round_trips_per_call":1,
            "new_order_engine_created":False,
            "new_signal_engine_created":False,
            "live_orders_submitted":0,
            "live_trading_enabled":False,
            "completed_at_utc":self._now().isoformat(),
        }
        self._append(result)
        return self._write_latest(result)
