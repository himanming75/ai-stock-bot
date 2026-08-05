from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


ALLOWED_SYMBOLS = {"SPY", "QQQ", "IWM"}


def create_micro_ticket(
    *,
    symbol: str,
    notional: Decimal,
    output_path: Path,
) -> dict:
    symbol = symbol.upper().strip()

    blockers: list[str] = []
    if symbol not in ALLOWED_SYMBOLS:
        blockers.append("SYMBOL_NOT_ALLOWED")
    if notional < Decimal("1"):
        blockers.append("NOTIONAL_BELOW_ONE_DOLLAR")
    if notional > Decimal("5"):
        blockers.append("NOTIONAL_ABOVE_FIVE_DOLLARS")

    canonical = f"{symbol}|buy|market|{notional}|day|p3-micro"
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    ticket = {
        "stage": "P3_MICRO_PAPER_TICKET",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "ticket_id": f"p3micro_{digest[:20]}",
        "client_order_id": f"p3m-{digest[:24]}",
        "idempotency_key": digest,
        "blocked": bool(blockers),
        "blockers": sorted(set(blockers)),
        "payload": {
            "symbol": symbol,
            "notional": format(notional, "f"),
            "side": "buy",
            "type": "market",
            "time_in_force": "day",
            "client_order_id": f"p3m-{digest[:24]}",
        },
        "actual_external_network_used": False,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(ticket, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ticket
