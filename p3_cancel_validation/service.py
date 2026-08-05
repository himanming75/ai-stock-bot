from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from pathlib import Path

from .client import AlpacaPaperCancelClient
from .token import consume_token, sha256_file, validate_token


OPEN_STATUSES = {
    "pending_new",
    "accepted",
    "new",
    "partially_filled",
    "pending_cancel",
}

TERMINAL_STATUSES = {
    "filled",
    "canceled",
    "expired",
    "rejected",
    "done_for_day",
    "replaced",
}


class P3PaperCancelValidationService:
    def __init__(self, client=None) -> None:
        self.client = client or AlpacaPaperCancelClient()

    def run(
        self,
        *,
        plan_path: Path,
        token_path: Path,
        nonce: str,
        output_dir: Path,
        poll_interval_seconds: int = 1,
        max_poll_cycles: int = 20,
    ) -> dict:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan_hash = sha256_file(plan_path)
        token, token_blockers = validate_token(
            token_path,
            plan_hash,
            nonce,
        )

        blockers = list(token_blockers)
        blockers.extend(plan.get("blockers", []))

        symbol = str(plan.get("symbol", "")).upper()
        notional = Decimal(str(plan.get("notional", "0")))
        multiplier = Decimal(str(plan.get("price_multiplier", "0")))
        client_order_id = str(plan.get("client_order_id", ""))

        clock = self.client.get_clock()
        account = self.client.get_account()
        asset = self.client.get_asset(symbol)
        latest = self.client.get_latest_trade(symbol)
        latest_price = Decimal(
            str((latest.get("trade") or {}).get("p") or "0")
        )

        if not clock.get("is_open", False):
            blockers.append("MARKET_NOT_OPEN")
        if account.get("status") != "ACTIVE":
            blockers.append("ACCOUNT_NOT_ACTIVE")
        if not asset.get("tradable", False):
            blockers.append("ASSET_NOT_TRADABLE")
        if not asset.get("fractionable", False):
            blockers.append("ASSET_NOT_FRACTIONABLE")
        if latest_price <= 0:
            blockers.append("LATEST_PRICE_INVALID")
        if notional < Decimal("1") or notional > Decimal("5"):
            blockers.append("NOTIONAL_LIMIT_VIOLATION")
        if multiplier <= 0 or multiplier > Decimal("0.80"):
            blockers.append("PRICE_MULTIPLIER_INVALID")

        duplicate = None
        duplicate_status, duplicate_payload = (
            self.client.get_order_by_client_id(client_order_id)
        )
        if duplicate_status == 200 and duplicate_payload:
            duplicate = duplicate_payload
            blockers.append("DUPLICATE_CLIENT_ORDER_ID")
        elif duplicate_status not in {404, 422}:
            blockers.append(
                f"DUPLICATE_CHECK_UNEXPECTED_STATUS:{duplicate_status}"
            )

        limit_price = (
            latest_price * multiplier
        ).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

        order_payload = {
            "symbol": symbol,
            "notional": format(notional, "f"),
            "side": "buy",
            "type": "limit",
            "limit_price": format(limit_price, "f"),
            "time_in_force": "day",
            "client_order_id": client_order_id,
            "extended_hours": False,
        }

        blockers = sorted(set(blockers))
        submitted = False
        broker_order = None
        submit_http_status = None
        cancel_http_status = None
        cancel_response = None
        status_history = []
        snapshots = []

        if not blockers:
            submit_http_status, broker_order = self.client.submit_order(
                order_payload
            )
            if submit_http_status not in {200, 201}:
                blockers.append(
                    f"ORDER_SUBMISSION_FAILED:{submit_http_status}"
                )
            else:
                submitted = True
                if token is not None:
                    consume_token(token_path, token)

        order_id = broker_order.get("id") if broker_order else None

        if submitted and order_id:
            for cycle in range(1, max_poll_cycles + 1):
                http_status, order = self.client.get_order(order_id)
                if http_status != 200 or not order:
                    blockers.append(
                        f"ORDER_READ_FAILED:{http_status}"
                    )
                    break

                status = str(order.get("status", "unknown"))
                if not status_history or status_history[-1] != status:
                    status_history.append(status)

                snapshot = {
                    "cycle": cycle,
                    "observed_at": datetime.now(timezone.utc).isoformat(),
                    "status": status,
                    "broker_order_id": order.get("id"),
                    "client_order_id": order.get("client_order_id"),
                    "filled_qty": order.get("filled_qty"),
                    "filled_avg_price": order.get("filled_avg_price"),
                }
                snapshots.append(snapshot)

                if status in OPEN_STATUSES:
                    break
                if status in TERMINAL_STATUSES:
                    break
                time.sleep(max(1, poll_interval_seconds))

            last_status = status_history[-1] if status_history else None
            if last_status in OPEN_STATUSES:
                cancel_http_status, cancel_response = (
                    self.client.cancel_order(order_id)
                )
                if cancel_http_status != 204:
                    blockers.append(
                        f"CANCEL_REQUEST_FAILED:{cancel_http_status}"
                    )
            elif last_status == "filled":
                blockers.append("ORDER_FILLED_BEFORE_CANCEL")
            else:
                blockers.append(
                    f"ORDER_NOT_CANCELABLE_STATUS:{last_status}"
                )

        final_order = None
        final_status = None
        if submitted and order_id:
            for cycle in range(1, max_poll_cycles + 1):
                http_status, order = self.client.get_order(order_id)
                if http_status != 200 or not order:
                    blockers.append(
                        f"FINAL_ORDER_READ_FAILED:{http_status}"
                    )
                    break

                final_order = order
                final_status = str(order.get("status", "unknown"))
                if (
                    not status_history
                    or status_history[-1] != final_status
                ):
                    status_history.append(final_status)

                if final_status in TERMINAL_STATUSES:
                    break
                time.sleep(max(1, poll_interval_seconds))

        canceled = final_status == "canceled"
        reconciled = bool(
            canceled
            and final_order
            and final_order.get("id") == order_id
            and final_order.get("client_order_id")
            == client_order_id
            and str(final_order.get("filled_qty") or "0")
            == "0"
        )

        result = {
            "stage": "P3_PAPER_CANCEL_VALIDATION",
            "status": (
                "PASS"
                if submitted
                and cancel_http_status == 204
                and canceled
                and reconciled
                and not blockers
                else "BLOCKED"
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "paper_endpoint_verified": True,
            "market_is_open": bool(clock.get("is_open", False)),
            "account_status": account.get("status"),
            "symbol": symbol,
            "latest_price": str(latest_price),
            "limit_price": str(limit_price),
            "price_multiplier": str(multiplier),
            "notional": str(notional),
            "order_payload": order_payload,
            "submitted": submitted,
            "submit_http_status": submit_http_status,
            "broker_order_id": order_id,
            "cancel_http_status": cancel_http_status,
            "cancel_response": cancel_response,
            "status_history": status_history,
            "pre_cancel_snapshots": snapshots,
            "final_status": final_status,
            "canceled": canceled,
            "reconciliation_matched": reconciled,
            "blockers": sorted(set(blockers)),
            "final_order": final_order,
            "actual_external_network_used": True,
            "actual_broker_read_performed": True,
            "actual_broker_write_performed": (
                submitted or cancel_http_status == 204
            ),
            "actual_order_submission_performed": submitted,
            "actual_order_cancel_performed": (
                cancel_http_status == 204
            ),
            "actual_paper_orders_submitted": 1 if submitted else 0,
            "actual_paper_orders_canceled": 1 if canceled else 0,
            "actual_live_orders_submitted": 0,
            "next_market_validation": (
                "P3_REJECT_AND_PARTIAL_FILL_VALIDATION"
            ),
            "next_fixed_development": (
                "PAPER_AUTOMATION_CONTROLLER_AND_SCHEDULER"
            ),
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "cancel_validation_result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with (output_dir / "cancel_validation_ledger.jsonl").open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(result, sort_keys=True) + "\n")

        return result
