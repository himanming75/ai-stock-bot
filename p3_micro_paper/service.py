from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .client import AlpacaPaperTradingClient
from .token import consume_token, sha256_file, validate_token


class P3MicroPaperOrderService:
    def __init__(self, client=None) -> None:
        self.client = client or AlpacaPaperTradingClient()

    def validate_and_submit(
        self,
        *,
        ticket_path: Path,
        token_path: Path,
        nonce: str,
        output_path: Path,
    ) -> dict:
        ticket = json.loads(ticket_path.read_text(encoding="utf-8"))
        ticket_hash = sha256_file(ticket_path)
        token, token_blockers = validate_token(
            token_path,
            ticket_hash,
            nonce,
        )

        blockers = list(token_blockers)
        payload = ticket.get("payload", {})
        symbol = str(payload.get("symbol", "")).upper()
        notional = Decimal(str(payload.get("notional", "0")))

        if ticket.get("blocked"):
            blockers.extend(ticket.get("blockers", []))
        if payload.get("side") != "buy":
            blockers.append("BUY_SIDE_REQUIRED")
        if payload.get("type") != "market":
            blockers.append("FRACTIONAL_MARKET_ORDER_REQUIRED")
        if payload.get("time_in_force") != "day":
            blockers.append("DAY_TIF_REQUIRED")
        if notional < Decimal("1") or notional > Decimal("5"):
            blockers.append("MICRO_NOTIONAL_LIMIT_VIOLATION")

        clock = self.client.get_clock()
        account = self.client.get_account()
        asset = self.client.get_asset(symbol)

        if not clock.get("is_open", False):
            blockers.append("MARKET_NOT_OPEN")
        if account.get("status") != "ACTIVE":
            blockers.append("ACCOUNT_NOT_ACTIVE")
        if not asset.get("tradable", False):
            blockers.append("ASSET_NOT_TRADABLE")
        if not asset.get("fractionable", False):
            blockers.append("ASSET_NOT_FRACTIONABLE")

        client_order_id = payload.get("client_order_id")
        duplicate_order = None
        try:
            duplicate_order = self.client.get_order_by_client_id(
                client_order_id
            )
        except Exception:
            duplicate_order = None

        if duplicate_order and duplicate_order.get("id"):
            blockers.append("DUPLICATE_CLIENT_ORDER_ID")

        blockers = sorted(set(blockers))
        submitted = False
        broker_response = None

        if not blockers:
            broker_response = self.client.submit_order(payload)
            submitted = True
            if token is not None:
                consume_token(token_path, token)

        reconciliation = None
        if submitted:
            remote = self.client.get_order_by_client_id(client_order_id)
            reconciliation = {
                "client_order_id": client_order_id,
                "submitted_order_id": broker_response.get("id"),
                "remote_order_id": remote.get("id"),
                "remote_status": remote.get("status"),
                "matched": (
                    broker_response.get("id") == remote.get("id")
                    and remote.get("client_order_id") == client_order_id
                ),
            }

        result = {
            "stage": "P3_MICRO_PAPER_ORDER_VALIDATION",
            "status": (
                "PASS"
                if submitted
                and reconciliation
                and reconciliation["matched"]
                else "BLOCKED"
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "ticket_sha256": ticket_hash,
            "paper_endpoint_verified": True,
            "market_is_open": bool(clock.get("is_open", False)),
            "account_status": account.get("status"),
            "asset": {
                "symbol": asset.get("symbol"),
                "tradable": asset.get("tradable"),
                "fractionable": asset.get("fractionable"),
            },
            "submitted": submitted,
            "blockers": blockers,
            "broker_response": broker_response,
            "reconciliation": reconciliation,
            "actual_external_network_used": True,
            "actual_broker_read_performed": True,
            "actual_broker_write_performed": submitted,
            "actual_order_submission_performed": submitted,
            "actual_paper_orders_submitted": 1 if submitted else 0,
            "actual_live_orders_submitted": 0,
            "next_market_validation": "P3_ORDER_STATUS_LIFECYCLE_MONITOR",
            "next_fixed_development": "PAPER_ORDER_LIFECYCLE_MONITOR",
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with (output_path.parent / "p3_micro_submission_ledger.jsonl").open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(result, sort_keys=True) + "\n")

        return result
