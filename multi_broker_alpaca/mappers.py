from __future__ import annotations
from decimal import Decimal
from multi_broker_core.models import AccountSnapshot, OrderSnapshot, PositionSnapshot
from multi_broker_core.symbols import normalize_equity_symbol


def D(value, default="0") -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def map_account(payload: dict) -> AccountSnapshot:
    return AccountSnapshot(
        broker="ALPACA",
        account_id=str(payload.get("id") or payload.get("account_number") or "UNKNOWN"),
        currency=str(payload.get("currency") or "USD"),
        equity=D(payload.get("equity")),
        cash=D(payload.get("cash")),
        buying_power=D(payload.get("buying_power")),
        status=str(payload.get("status") or "UNKNOWN").upper(),
    )


def map_position(payload: dict, account_id: str) -> PositionSnapshot:
    return PositionSnapshot(
        broker="ALPACA",
        account_id=account_id,
        symbol=normalize_equity_symbol(str(payload.get("symbol", ""))),
        quantity=D(payload.get("qty")),
        average_price=D(payload.get("avg_entry_price")),
        market_value=D(payload.get("market_value")),
        unrealized_pl=D(payload.get("unrealized_pl")),
    )


def map_order(payload: dict, account_id: str) -> OrderSnapshot:
    return OrderSnapshot(
        broker="ALPACA",
        account_id=account_id,
        order_id=str(payload.get("id") or payload.get("client_order_id") or "UNKNOWN"),
        symbol=normalize_equity_symbol(str(payload.get("symbol", ""))),
        side=str(payload.get("side") or "UNKNOWN").upper(),
        quantity=D(payload.get("qty")),
        filled_quantity=D(payload.get("filled_qty")),
        status=str(payload.get("status") or "UNKNOWN").upper(),
    )
