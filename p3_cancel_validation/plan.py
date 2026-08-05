from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


ALLOWED_SYMBOLS = {"SPY", "QQQ", "IWM"}


def create_cancel_plan(
    *,
    symbol: str,
    notional: Decimal,
    price_multiplier: Decimal,
    output_path: Path,
) -> dict:
    symbol = symbol.strip().upper()
    blockers = []

    if symbol not in ALLOWED_SYMBOLS:
        blockers.append("SYMBOL_NOT_ALLOWED")
    if notional < Decimal("1") or notional > Decimal("5"):
        blockers.append("NOTIONAL_LIMIT_VIOLATION")
    if price_multiplier <= Decimal("0") or price_multiplier > Decimal("0.80"):
        blockers.append("PRICE_MULTIPLIER_TOO_HIGH_OR_INVALID")

    canonical = (
        f"{symbol}|{notional}|{price_multiplier}|"
        "buy|limit|day|p3-cancel"
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    plan = {
        "stage": "P3_PAPER_CANCEL_VALIDATION_PLAN",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "plan_id": f"p3cancel_{digest[:20]}",
        "client_order_id": f"p3c-{digest[:24]}",
        "idempotency_key": digest,
        "symbol": symbol,
        "notional": format(notional, "f"),
        "price_multiplier": format(price_multiplier, "f"),
        "blocked": bool(blockers),
        "blockers": sorted(set(blockers)),
        "actual_external_network_used": False,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return plan
