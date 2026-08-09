from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from paper_order_lifecycle.client import AlpacaPaperReadClient
from paper_order_lifecycle.service import TERMINAL_STATUSES


class FinalExitFillReconciliationRoundTripLedgerV2127:
    """
    Read-only final reconciliation for a V2.1.25 Alpaca Paper exit order.

    Sources:
      - V2.1.23 latest lifecycle: actual entry fill
      - V2.1.25 exit ledger: submitted exit order
      - AlpacaPaperReadClient: actual exit order + positions/account/clock

    A completed round-trip record is immutable/deduplicated by round_trip_id.

    This stage NEVER submits an order.
    """

    def __init__(
        self,
        root,
        *,
        client_factory=None,
        sleep_fn=None,
        now_fn=None,
    ):
        self.root=Path(root)
        self.entry_lifecycle_latest=(
            self.root/"runtime"/"alpaca_paper_order_position_lifecycle_v2_1_23"/
            "latest_lifecycle.json"
        )
        self.exit_ledger_source=(
            self.root/"runtime"/"alpaca_paper_exit_recovery_v2_1_25"/
            "exit_ledger.jsonl"
        )
        self.v2126_state_path=(
            self.root/"runtime"/"full_alpaca_paper_round_trip_v2_1_26"/
            "cycle_state.json"
        )

        self.runtime_dir=(
            self.root/"runtime"/"final_round_trip_ledger_v2_1_27"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.exit_monitor_ledger=(
            self.runtime_dir/"exit_fill_reconciliation_ledger.jsonl"
        )
        self.completed_ledger=(
            self.runtime_dir/"completed_round_trips.jsonl"
        )
        self.latest=self.runtime_dir/"latest_round_trip.json"
        self.summary_path=self.runtime_dir/"latest_reconciliation_summary.json"

        self.client_factory=client_factory or AlpacaPaperReadClient
        self.sleep_fn=sleep_fn or time.sleep
        self.now_fn=now_fn or (lambda:datetime.now(timezone.utc))

    @staticmethod
    def _read_json(path):
        return json.loads(path.read_text(encoding="utf-8-sig"))

    @staticmethod
    def _decimal(value, field):
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            raise RuntimeError(f"INVALID_DECIMAL_{field.upper()}")

    @staticmethod
    def _dt(value):
        if not value:
            return None
        return datetime.fromisoformat(str(value).replace("Z","+00:00")).astimezone(timezone.utc)

    def _exit_submission_rows(self):
        if not self.exit_ledger_source.exists():
            return []
        rows=[]
        for line in self.exit_ledger_source.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row=json.loads(line)
            if row.get("paper_exit_order_submitted") is True:
                rows.append(row)
        return rows

    def _latest_exit_submission(self):
        rows=self._exit_submission_rows()
        return rows[-1] if rows else None

    def _completed_ids(self):
        if not self.completed_ledger.exists():
            return set()
        out=set()
        for line in self.completed_ledger.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row=json.loads(line)
            except Exception:
                continue
            if row.get("round_trip_id"):
                out.add(str(row["round_trip_id"]))
        return out

    def _write_summary(self,row):
        self.summary_path.write_text(
            json.dumps(row,indent=2,sort_keys=True,ensure_ascii=False,default=str),
            encoding="utf-8",
        )
        return row

    def _append_exit_snapshot(self,row):
        with self.exit_monitor_ledger.open("a",encoding="utf-8") as f:
            f.write(json.dumps(row,sort_keys=True,default=str)+"\n")

    def _append_completed_once(self,row):
        round_trip_id=str(row["round_trip_id"])
        if round_trip_id in self._completed_ids():
            return False
        with self.completed_ledger.open("a",encoding="utf-8") as f:
            f.write(json.dumps(row,sort_keys=True,default=str)+"\n")
        self.latest.write_text(
            json.dumps(row,indent=2,sort_keys=True,default=str),
            encoding="utf-8",
        )
        return True

    def build_plan(self):
        if not self.entry_lifecycle_latest.exists():
            return self._write_summary({
                "status":"WAITING_FOR_V2_1_23_ENTRY_LIFECYCLE",
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            })

        exit_submission=self._latest_exit_submission()
        if exit_submission is None:
            return self._write_summary({
                "status":"WAITING_FOR_V2_1_25_EXIT_SUBMISSION",
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            })

        entry_life=self._read_json(self.entry_lifecycle_latest)
        entry_summary=entry_life.get("order_lifecycle_summary") or {}
        entry_snapshot=entry_summary.get("final_snapshot") or {}

        if not (
            entry_life.get("status")=="PASS_ORDER_POSITION_LIFECYCLE_READ_ONLY"
            and entry_summary.get("final_status")=="filled"
            and entry_snapshot.get("filled_avg_price") is not None
            and self._decimal(entry_snapshot.get("filled_qty") or "0","entry_filled_qty")>0
        ):
            return self._write_summary({
                "status":"BLOCKED_ENTRY_FILL_NOT_RECONCILED",
                "entry_lifecycle_status":entry_life.get("status"),
                "entry_final_status":entry_summary.get("final_status"),
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            })

        exit_order=exit_submission.get("exit_order") or {}
        exit_client_order_id=str(exit_order.get("client_order_id") or "").strip()
        exit_broker_order_id=str(exit_order.get("id") or "").strip()
        symbol=str(exit_submission.get("symbol") or entry_snapshot.get("symbol") or "").upper().strip()
        evidence_key=str(exit_submission.get("evidence_key") or "").strip()

        if not exit_client_order_id or not exit_broker_order_id or not symbol or not evidence_key:
            return self._write_summary({
                "status":"BLOCKED_EXIT_ORDER_BINDING_MISSING",
                "exit_client_order_id":exit_client_order_id or None,
                "exit_broker_order_id":exit_broker_order_id or None,
                "symbol":symbol or None,
                "evidence_key":evidence_key or None,
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            })

        round_trip_seed={
            "evidence_key":evidence_key,
            "symbol":symbol,
            "entry_broker_order_id":entry_snapshot.get("broker_order_id"),
            "entry_client_order_id":entry_snapshot.get("client_order_id"),
            "exit_broker_order_id":exit_broker_order_id,
            "exit_client_order_id":exit_client_order_id,
        }
        round_trip_id=hashlib.sha256(
            json.dumps(round_trip_seed,sort_keys=True,separators=(",",":"),default=str).encode("utf-8")
        ).hexdigest()

        if round_trip_id in self._completed_ids():
            return self._write_summary({
                "status":"ROUND_TRIP_ALREADY_COMPLETED_NO_DUPLICATE",
                "round_trip_id":round_trip_id,
                "symbol":symbol,
                "evidence_key":evidence_key,
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            })

        return self._write_summary({
            "status":"READY_FOR_READ_ONLY_EXIT_FILL_RECONCILIATION",
            "round_trip_id":round_trip_id,
            "symbol":symbol,
            "evidence_key":evidence_key,
            "entry_client_order_id":entry_snapshot.get("client_order_id"),
            "entry_broker_order_id":entry_snapshot.get("broker_order_id"),
            "exit_client_order_id":exit_client_order_id,
            "exit_broker_order_id":exit_broker_order_id,
            "exit_reason":exit_submission.get("exit_reason"),
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        })

    def reconcile(self, *, interval_seconds=5, max_cycles=12):
        plan=self.build_plan()
        if plan.get("status")!="READY_FOR_READ_ONLY_EXIT_FILL_RECONCILIATION":
            return plan

        client=self.client_factory()
        snapshots=[]

        for cycle in range(1,max_cycles+1):
            order=client.get_order_by_client_id(plan["exit_client_order_id"])
            positions=client.get_positions()
            account=client.get_account()
            clock=client.get_clock()

            symbol=str(order.get("symbol") or plan["symbol"]).upper()
            matching_position=next(
                (p for p in positions if str(p.get("symbol") or "").upper()==symbol),
                None,
            )
            status=str(order.get("status") or "unknown")
            filled_qty=self._decimal(order.get("filled_qty") or "0","exit_filled_qty")
            filled_avg_price=(
                self._decimal(order.get("filled_avg_price"),"exit_filled_avg_price")
                if order.get("filled_avg_price") is not None
                else None
            )

            snapshot={
                "cycle_number":cycle,
                "observed_at_utc":self.now_fn().astimezone(timezone.utc).isoformat(),
                "round_trip_id":plan["round_trip_id"],
                "symbol":symbol,
                "exit_client_order_id":plan["exit_client_order_id"],
                "exit_broker_order_id":order.get("id"),
                "exit_broker_order_id_matches":str(order.get("id") or "")==plan["exit_broker_order_id"],
                "status":status,
                "terminal":status in TERMINAL_STATUSES,
                "filled_qty":str(filled_qty),
                "filled_avg_price":str(filled_avg_price) if filled_avg_price is not None else None,
                "submitted_at":order.get("submitted_at"),
                "filled_at":order.get("filled_at"),
                "position_found_after_exit":matching_position is not None,
                "remaining_position":matching_position,
                "account_equity":account.get("equity"),
                "account_cash":account.get("cash"),
                "market_is_open":bool(clock.get("is_open",False)),
                "actual_external_network_used":True,
                "actual_broker_read_performed":True,
                "actual_broker_write_performed":False,
                "actual_order_submission_performed":False,
                "actual_paper_orders_submitted":0,
                "actual_live_orders_submitted":0,
            }
            snapshots.append(snapshot)
            self._append_exit_snapshot(snapshot)

            if snapshot["terminal"]:
                break
            if cycle<max_cycles:
                self.sleep_fn(max(1,interval_seconds))

        last=snapshots[-1] if snapshots else None
        if not last:
            return self._write_summary({
                **plan,
                "status":"BLOCKED_EXIT_RECONCILIATION_NO_SNAPSHOT",
                "broker_network_used":True,
            })

        if last["status"]!="filled":
            return self._write_summary({
                **plan,
                "status":"BLOCKED_EXIT_NOT_FILLED",
                "exit_final_snapshot":last,
                "broker_network_used":True,
            })

        if not last["exit_broker_order_id_matches"]:
            return self._write_summary({
                **plan,
                "status":"BLOCKED_EXIT_BROKER_ORDER_ID_MISMATCH",
                "exit_final_snapshot":last,
                "broker_network_used":True,
            })

        if self._decimal(last["filled_qty"],"exit_filled_qty")<=0 or last["filled_avg_price"] is None:
            return self._write_summary({
                **plan,
                "status":"BLOCKED_EXIT_FILL_FIELDS_INVALID",
                "exit_final_snapshot":last,
                "broker_network_used":True,
            })

        if last["position_found_after_exit"]:
            return self._write_summary({
                **plan,
                "status":"BLOCKED_EXIT_FILLED_BUT_POSITION_REMAINS",
                "exit_final_snapshot":last,
                "broker_network_used":True,
            })

        return self._complete_round_trip(plan,last)

    def _complete_round_trip(self,plan,exit_snapshot):
        entry_life=self._read_json(self.entry_lifecycle_latest)
        entry_summary=entry_life["order_lifecycle_summary"]
        entry=entry_summary["final_snapshot"]
        exit_submission=self._latest_exit_submission()

        entry_qty=self._decimal(entry["filled_qty"],"entry_filled_qty")
        exit_qty=self._decimal(exit_snapshot["filled_qty"],"exit_filled_qty")
        entry_price=self._decimal(entry["filled_avg_price"],"entry_filled_avg_price")
        exit_price=self._decimal(exit_snapshot["filled_avg_price"],"exit_filled_avg_price")

        # V2.1.22 currently supports long BUY entry only. A completed close is
        # reconciled using the smaller actual filled quantity if broker fill
        # quantities differ unexpectedly; mismatch is made explicit.
        matched_qty=min(entry_qty,exit_qty)
        gross_pnl=(exit_price-entry_price)*matched_qty
        entry_notional=entry_price*matched_qty
        return_pct=(gross_pnl/entry_notional*Decimal("100")) if entry_notional>0 else Decimal("0")

        entry_filled_at=self._dt(entry.get("filled_at"))
        exit_filled_at=self._dt(exit_snapshot.get("filled_at"))
        holding_seconds=(
            max(0.0,(exit_filled_at-entry_filled_at).total_seconds())
            if entry_filled_at and exit_filled_at
            else None
        )

        completed_at=self.now_fn().astimezone(timezone.utc)
        row={
            "stage":"BROKER_INTEGRATION_V2_1_27_COMPLETED_ROUND_TRIP",
            "status":"COMPLETED_ALPACA_PAPER_ROUND_TRIP",
            "round_trip_id":plan["round_trip_id"],
            "evidence_key":plan["evidence_key"],
            "symbol":plan["symbol"],
            "entry":{
                "client_order_id":entry.get("client_order_id"),
                "broker_order_id":entry.get("broker_order_id"),
                "side":entry.get("side"),
                "filled_qty":str(entry_qty),
                "filled_avg_price":str(entry_price),
                "submitted_at":entry.get("submitted_at"),
                "filled_at":entry.get("filled_at"),
            },
            "exit":{
                "client_order_id":exit_snapshot.get("exit_client_order_id"),
                "broker_order_id":exit_snapshot.get("exit_broker_order_id"),
                "side":"sell",
                "filled_qty":str(exit_qty),
                "filled_avg_price":str(exit_price),
                "submitted_at":exit_snapshot.get("submitted_at"),
                "filled_at":exit_snapshot.get("filled_at"),
                "reason":exit_submission.get("exit_reason"),
            },
            "quantity_reconciliation":{
                "entry_filled_qty":str(entry_qty),
                "exit_filled_qty":str(exit_qty),
                "matched_qty_for_pnl":str(matched_qty),
                "exact_match":entry_qty==exit_qty,
            },
            "holding_seconds":holding_seconds,
            "gross_pnl_from_fills":str(gross_pnl),
            "return_pct_from_fills":str(return_pct),
            "fees_included":False,
            "pnl_semantics":"FILL_BASED_GROSS_PNL_BEFORE_FEES",
            "paper_only":True,
            "broker_read_performed":True,
            "broker_write_performed_from_stage":False,
            "paper_orders_submitted_from_stage":0,
            "live_orders_submitted_from_stage":0,
            "completed_at_utc":completed_at.isoformat(),
        }

        appended=self._append_completed_once(row)
        row["new_completed_ledger_row"]=appended

        self._mark_v2126_complete(plan["round_trip_id"],completed_at)

        return self._write_summary({
            "status":"PASS_FINAL_EXIT_FILL_RECONCILIATION",
            "round_trip_id":plan["round_trip_id"],
            "completed_round_trip":row,
            "completed_ledger":str(self.completed_ledger),
            "latest_round_trip":str(self.latest),
            "broker_network_used":True,
            "broker_write_performed":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        })

    def _mark_v2126_complete(self,round_trip_id,completed_at):
        if not self.v2126_state_path.exists():
            return
        try:
            state=self._read_json(self.v2126_state_path)
        except Exception:
            return
        state["phase"]="ROUND_TRIP_COMPLETE"
        state["round_trip_complete"]=True
        state["final_round_trip_id"]=round_trip_id
        state["final_fill_reconciled"]=True
        state["updated_at_utc"]=completed_at.isoformat()
        self.v2126_state_path.write_text(
            json.dumps(state,indent=2,sort_keys=True,default=str),
            encoding="utf-8",
        )
