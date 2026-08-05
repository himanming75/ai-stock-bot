from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .client import AlpacaPaperReadClient


TERMINAL_STATUSES = {
    "filled",
    "canceled",
    "expired",
    "rejected",
    "done_for_day",
    "replaced",
}

KNOWN_STATUSES = {
    "new",
    "accepted",
    "pending_new",
    "partially_filled",
    "filled",
    "canceled",
    "expired",
    "rejected",
    "pending_cancel",
    "pending_replace",
    "replaced",
    "done_for_day",
    "stopped",
    "suspended",
    "calculated",
    "held",
}


class PaperOrderLifecycleMonitor:
    def __init__(self, client=None) -> None:
        self.client = client or AlpacaPaperReadClient()

    def _extract_client_order_id(self, p3_result: dict) -> str:
        response = p3_result.get("broker_response") or {}
        client_order_id = response.get("client_order_id")
        if not client_order_id:
            reconciliation = p3_result.get("reconciliation") or {}
            client_order_id = reconciliation.get("client_order_id")
        if not client_order_id:
            raise RuntimeError("CLIENT_ORDER_ID_NOT_FOUND_IN_P3_RESULT")
        return str(client_order_id)

    def monitor(
        self,
        *,
        p3_result_path: Path,
        output_dir: Path,
        interval_seconds: int = 5,
        max_cycles: int = 12,
    ) -> dict:
        p3_result = json.loads(
            p3_result_path.read_text(encoding="utf-8")
        )
        client_order_id = self._extract_client_order_id(p3_result)

        output_dir.mkdir(parents=True, exist_ok=True)
        ledger_path = output_dir / "order_lifecycle_ledger.jsonl"
        snapshots = []
        status_history = []

        for cycle in range(1, max_cycles + 1):
            order = self.client.get_order_by_client_id(
                client_order_id
            )
            account = self.client.get_account()
            positions = self.client.get_positions()
            clock = self.client.get_clock()

            symbol = str(order.get("symbol", ""))
            matching_position = next(
                (
                    position
                    for position in positions
                    if str(position.get("symbol", "")) == symbol
                ),
                None,
            )

            status = str(order.get("status", "unknown"))
            if not status_history or status_history[-1] != status:
                status_history.append(status)

            filled_qty = Decimal(str(order.get("filled_qty") or "0"))
            filled_avg_price = (
                Decimal(str(order.get("filled_avg_price")))
                if order.get("filled_avg_price") is not None
                else None
            )

            snapshot = {
                "cycle_number": cycle,
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "client_order_id": client_order_id,
                "broker_order_id": order.get("id"),
                "symbol": symbol,
                "side": order.get("side"),
                "order_type": order.get("type") or order.get("order_type"),
                "status": status,
                "known_status": status in KNOWN_STATUSES,
                "terminal": status in TERMINAL_STATUSES,
                "notional": order.get("notional"),
                "qty": order.get("qty"),
                "filled_qty": str(filled_qty),
                "filled_avg_price": (
                    str(filled_avg_price)
                    if filled_avg_price is not None
                    else None
                ),
                "submitted_at": order.get("submitted_at"),
                "filled_at": order.get("filled_at"),
                "canceled_at": order.get("canceled_at"),
                "failed_at": order.get("failed_at"),
                "account_equity": account.get("equity"),
                "account_cash": account.get("cash"),
                "position_found": matching_position is not None,
                "position": matching_position,
                "market_is_open": bool(clock.get("is_open", False)),
                "actual_external_network_used": True,
                "actual_broker_read_performed": True,
                "actual_broker_write_performed": False,
                "actual_order_submission_performed": False,
                "actual_paper_orders_submitted": 0,
                "actual_live_orders_submitted": 0,
            }
            snapshots.append(snapshot)

            with ledger_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(snapshot, sort_keys=True) + "\n"
                )

            cycle_path = output_dir / f"cycle_{cycle:04d}.json"
            cycle_path.write_text(
                json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            print(
                json.dumps(snapshot, indent=2, sort_keys=True),
                flush=True,
            )

            if snapshot["terminal"]:
                break
            if cycle < max_cycles:
                time.sleep(max(1, interval_seconds))

        last = snapshots[-1] if snapshots else None
        terminal = bool(last and last["terminal"])
        matched_order_id = (
            last
            and last["broker_order_id"]
            == (p3_result.get("broker_response") or {}).get("id")
        )

        fill_consistent = True
        if last and last["status"] == "filled":
            fill_consistent = (
                Decimal(last["filled_qty"]) > 0
                and last["filled_avg_price"] is not None
                and last["position_found"]
            )

        summary = {
            "stage": "PAPER_ORDER_LIFECYCLE_MONITOR",
            "status": (
                "PASS"
                if last
                and terminal
                and matched_order_id
                and fill_consistent
                else "BLOCKED"
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "client_order_id": client_order_id,
            "completed_cycles": len(snapshots),
            "status_history": status_history,
            "terminal_status_reached": terminal,
            "final_status": last["status"] if last else None,
            "broker_order_id_matched": bool(matched_order_id),
            "fill_reconciliation_pass": bool(fill_consistent),
            "final_snapshot": last,
            "actual_external_network_used": True,
            "actual_broker_read_performed": True,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_market_validation": (
                "P3_CANCEL_REJECT_PARTIAL_FILL_VALIDATION"
            ),
            "next_fixed_development": (
                "PAPER_AUTOMATION_CONTROLLER_AND_SCHEDULER"
            ),
        }

        (output_dir / "order_lifecycle_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return summary
