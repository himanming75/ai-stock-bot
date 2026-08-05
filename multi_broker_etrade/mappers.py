from __future__ import annotations
from decimal import Decimal
from multi_broker_core.models import AccountSnapshot, OrderSnapshot, PositionSnapshot
from multi_broker_core.symbols import normalize_equity_symbol


def D(value, default="0") -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def nested(payload: dict, *keys, default=None):
    current = payload
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def map_account(account: dict, balance: dict | None = None) -> AccountSnapshot:
    balance = balance or {}
    account_id = str(
        account.get("accountIdKey")
        or account.get("accountId")
        or "UNKNOWN"
    )
    return AccountSnapshot(
        broker="ETRADE",
        account_id=account_id,
        currency="USD",
        equity=D(
            nested(balance, "Computed", "RealTimeValues", "totalAccountValue")
            or balance.get("totalAccountValue")
        ),
        cash=D(
            nested(balance, "Computed", "cashAvailableForInvestment")
            or balance.get("cashAvailableForInvestment")
        ),
        buying_power=D(
            nested(balance, "Computed", "cashAvailableForInvestment")
            or balance.get("buyingPower")
        ),
        status=str(account.get("accountStatus") or "ACTIVE").upper(),
    )


def map_position(position: dict, account_id: str) -> PositionSnapshot:
    product = position.get("Product") or position.get("product") or {}
    symbol = (
        product.get("symbol")
        or position.get("symbol")
        or position.get("symbolDescription")
        or ""
    )
    quantity = (
        position.get("quantity")
        or position.get("qty")
        or position.get("positionQuantity")
        or 0
    )
    return PositionSnapshot(
        broker="ETRADE",
        account_id=account_id,
        symbol=normalize_equity_symbol(str(symbol)),
        quantity=D(quantity),
        average_price=D(
            position.get("pricePaid")
            or position.get("averagePrice")
            or position.get("costPerShare")
        ),
        market_value=D(
            position.get("marketValue")
            or position.get("totalGain")
            or 0
        ),
        unrealized_pl=D(
            position.get("totalGain")
            or position.get("unrealizedGain")
            or 0
        ),
    )


def map_order(order: dict, account_id: str) -> OrderSnapshot:
    detail = {}
    details = order.get("OrderDetail") or order.get("orderDetail") or []
    if isinstance(details, list) and details:
        detail = details[0]
    elif isinstance(details, dict):
        detail = details

    instruments = detail.get("Instrument") or detail.get("instrument") or []
    instrument = instruments[0] if isinstance(instruments, list) and instruments else {}
    product = instrument.get("Product") or instrument.get("product") or {}

    return OrderSnapshot(
        broker="ETRADE",
        account_id=account_id,
        order_id=str(order.get("orderId") or order.get("id") or "UNKNOWN"),
        symbol=normalize_equity_symbol(
            str(product.get("symbol") or instrument.get("symbol") or "UNKNOWN")
        ),
        side=str(
            instrument.get("orderAction")
            or detail.get("orderAction")
            or "UNKNOWN"
        ).upper(),
        quantity=D(
            instrument.get("orderedQuantity")
            or detail.get("orderedQuantity")
            or 0
        ),
        filled_quantity=D(
            instrument.get("filledQuantity")
            or detail.get("filledQuantity")
            or 0
        ),
        status=str(
            detail.get("status")
            or order.get("orderStatus")
            or "UNKNOWN"
        ).upper(),
    )
