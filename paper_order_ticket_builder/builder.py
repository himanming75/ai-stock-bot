from __future__ import annotations
from decimal import Decimal, ROUND_DOWN

from .ids import client_order_id, idempotency_key
from .models import D, text
from .validation import validate_payload

def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_DOWN)

def build_ticket(
    *,
    plan: dict,
    child: dict,
    market: dict,
    policy: dict,
) -> dict:
    symbol = str(child.get("symbol", plan.get("symbol", ""))).upper()
    side = str(child.get("side", plan.get("side", ""))).lower()
    sequence = int(child.get("sequence", 1))
    planned_notional = quantize_money(D(child.get("planned_notional")))
    order_type = str(child.get("order_type", "limit")).lower()
    tif = str(child.get("time_in_force", "day")).lower()
    latest_price = D(market.get("latest_price"))
    offset_bps = D(policy.get("limit_offset_bps", "5"))

    limit_price = None
    if order_type == "limit" and latest_price > 0:
        multiplier = (
            Decimal("1") - offset_bps / Decimal("10000")
            if side == "buy"
            else Decimal("1") + offset_bps / Decimal("10000")
        )
        limit_price = quantize_money(latest_price * multiplier)

    payload = {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "time_in_force": tif,
        "notional": text(planned_notional),
        "extended_hours": bool(policy.get("extended_hours", False)),
        "client_order_id": client_order_id(
            plan_id=str(plan.get("plan_id", "")),
            symbol=symbol,
            side=side,
            sequence=sequence,
        ),
        "submission_enabled": False,
        "broker_write_allowed": False,
    }
    if limit_price is not None:
        payload["limit_price"] = text(limit_price)

    blockers = validate_payload(payload, policy)
    return {
        "ticket_id": f"ticket_{payload['client_order_id']}",
        "parent_plan_id": plan.get("plan_id"),
        "child_sequence": sequence,
        "payload": payload,
        "idempotency_key": idempotency_key(payload),
        "status": "VALID" if not blockers else "BLOCKED",
        "blockers": blockers,
        "broker_endpoint": "https://paper-api.alpaca.markets",
        "paper_endpoint_only": True,
        "submission_enabled": False,
        "broker_write_allowed": False,
    }
