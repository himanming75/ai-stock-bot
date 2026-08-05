from __future__ import annotations
from .models import D

ALLOWED_SIDES = {"buy", "sell"}
ALLOWED_TYPES = {"market", "limit", "stop", "stop_limit"}
ALLOWED_TIFS = {"day", "gtc", "opg", "cls", "ioc", "fok"}

def validate_payload(payload: dict, policy: dict) -> list[str]:
    blockers = []
    symbol = str(payload.get("symbol", "")).upper()
    side = str(payload.get("side", "")).lower()
    order_type = str(payload.get("type", "")).lower()
    tif = str(payload.get("time_in_force", "")).lower()
    notional = D(payload.get("notional"))
    qty = D(payload.get("qty"))
    limit_price = D(payload.get("limit_price"))

    if not symbol or not symbol.replace(".", "").isalnum():
        blockers.append("SYMBOL_INVALID")
    if side not in ALLOWED_SIDES:
        blockers.append("SIDE_INVALID")
    if order_type not in ALLOWED_TYPES:
        blockers.append("ORDER_TYPE_INVALID")
    if tif not in ALLOWED_TIFS:
        blockers.append("TIME_IN_FORCE_INVALID")
    if notional > 0 and qty > 0:
        blockers.append("QTY_AND_NOTIONAL_MUTUALLY_EXCLUSIVE")
    if notional <= 0 and qty <= 0:
        blockers.append("QTY_OR_NOTIONAL_REQUIRED")
    if notional > D(policy.get("max_ticket_notional", "500")):
        blockers.append("TICKET_NOTIONAL_LIMIT_EXCEEDED")
    if order_type in {"limit", "stop_limit"} and limit_price <= 0:
        blockers.append("LIMIT_PRICE_REQUIRED")
    if payload.get("extended_hours") is True:
        if tif != "day" or order_type != "limit":
            blockers.append("EXTENDED_HOURS_REQUIRES_DAY_LIMIT")
    if payload.get("submission_enabled") is not False:
        blockers.append("SUBMISSION_MUST_BE_DISABLED")
    if payload.get("broker_write_allowed") is not False:
        blockers.append("BROKER_WRITE_MUST_BE_DISABLED")
    return blockers
