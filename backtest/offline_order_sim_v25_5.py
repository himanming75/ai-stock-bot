from __future__ import annotations

"""
V25.5 Offline Order Simulator

Deterministic simulation for MARKET, LIMIT, STOP, and STOP_LIMIT orders.
Supports partial fills, commission, slippage, time-in-force, cancellation,
expiry, immutable event hashes, persistence, and tamper detection.

No network, account, broker, or live-execution functionality is present.
"""

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
from typing import Any
import json

VERSION = "25.5"
ZERO = Decimal("0")
CENT = Decimal("0.01")
QTY_STEP = Decimal("0.000001")


class OrderSimError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise OrderSimError(f"invalid decimal: {value!r}") from exc
    if not result.is_finite():
        raise OrderSimError("decimal must be finite")
    return result


def _money(value: Any) -> Decimal:
    return _d(value).quantize(CENT, rounding=ROUND_HALF_UP)


def _qty(value: Any) -> Decimal:
    return _d(value).quantize(QTY_STEP, rounding=ROUND_DOWN)


def _canon(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canon(payload).encode("utf-8")).hexdigest()


def _symbol(value: str) -> str:
    result = value.strip().upper()
    if not result or len(result) > 15 or not all(c.isalnum() or c in ".-" for c in result):
        raise OrderSimError("invalid symbol")
    return result


@dataclass(frozen=True)
class ExecutionPolicy:
    commission_per_order: Decimal = Decimal("1.00")
    slippage_bps: Decimal = Decimal("5")
    participation_rate: Decimal = Decimal("0.25")
    allow_fractional: bool = True

    def __post_init__(self) -> None:
        if _d(self.commission_per_order) < ZERO:
            raise OrderSimError("commission cannot be negative")
        if _d(self.slippage_bps) < ZERO:
            raise OrderSimError("slippage cannot be negative")
        if _d(self.participation_rate) <= ZERO or _d(self.participation_rate) > Decimal("1"):
            raise OrderSimError("participation_rate must be within (0, 1]")


@dataclass(frozen=True)
class Bar:
    timestamp: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class Order:
    order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    limit_price: Decimal | None
    stop_price: Decimal | None
    tif: str
    created_index: int
    expire_index: int | None
    status: str
    filled_quantity: Decimal
    average_fill_price: Decimal
    commission_paid: Decimal
    triggered: bool
    previous_hash: str
    order_hash: str


@dataclass(frozen=True)
class Fill:
    order_id: str
    bar_index: int
    quantity: Decimal
    price: Decimal
    commission: Decimal
    fill_hash: str


def _order_payload(order: Order, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "order_id": order.order_id,
        "symbol": order.symbol,
        "side": order.side,
        "order_type": order.order_type,
        "quantity": str(order.quantity),
        "limit_price": None if order.limit_price is None else str(order.limit_price),
        "stop_price": None if order.stop_price is None else str(order.stop_price),
        "tif": order.tif,
        "created_index": order.created_index,
        "expire_index": order.expire_index,
        "status": order.status,
        "filled_quantity": str(order.filled_quantity),
        "average_fill_price": str(order.average_fill_price),
        "commission_paid": str(order.commission_paid),
        "triggered": order.triggered,
        "previous_hash": order.previous_hash,
    }
    if include_hash:
        payload["order_hash"] = order.order_hash
    return payload


def _fill_payload(fill: Fill, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "order_id": fill.order_id,
        "bar_index": fill.bar_index,
        "quantity": str(fill.quantity),
        "price": str(fill.price),
        "commission": str(fill.commission),
    }
    if include_hash:
        payload["fill_hash"] = fill.fill_hash
    return payload


def _finalize_order(order: Order) -> Order:
    clean = replace(order, order_hash="")
    return replace(clean, order_hash=_hash(_order_payload(clean)))


def create_order(
    order_id: str,
    symbol: str,
    side: str,
    order_type: str,
    quantity: Any,
    *,
    limit_price: Any | None = None,
    stop_price: Any | None = None,
    tif: str = "GTC",
    created_index: int = 0,
    expire_index: int | None = None,
    previous_hash: str = "GENESIS",
    allow_fractional: bool = True,
) -> Order:
    oid = order_id.strip()
    if not oid:
        raise OrderSimError("order_id required")
    sym = _symbol(symbol)
    side_n = side.upper()
    type_n = order_type.upper()
    tif_n = tif.upper()
    if side_n not in {"BUY", "SELL"}:
        raise OrderSimError("side must be BUY or SELL")
    if type_n not in {"MARKET", "LIMIT", "STOP", "STOP_LIMIT"}:
        raise OrderSimError("unsupported order type")
    if tif_n not in {"GTC", "DAY", "IOC"}:
        raise OrderSimError("unsupported time in force")
    qty = _qty(quantity)
    if qty <= ZERO:
        raise OrderSimError("quantity must be positive")
    if not allow_fractional and qty != qty.to_integral_value():
        raise OrderSimError("fractional quantity disabled")

    lp = None if limit_price is None else _money(limit_price)
    sp = None if stop_price is None else _money(stop_price)
    if type_n in {"LIMIT", "STOP_LIMIT"} and (lp is None or lp <= ZERO):
        raise OrderSimError("limit price required")
    if type_n in {"STOP", "STOP_LIMIT"} and (sp is None or sp <= ZERO):
        raise OrderSimError("stop price required")
    if created_index < 0:
        raise OrderSimError("created_index cannot be negative")
    if expire_index is not None and expire_index < created_index:
        raise OrderSimError("expire_index cannot precede created_index")

    return _finalize_order(Order(
        oid, sym, side_n, type_n, qty, lp, sp, tif_n, created_index,
        expire_index, "PENDING", ZERO, ZERO, ZERO, False, previous_hash, ""
    ))


def _validate_bar(bar: Bar) -> Bar:
    o, h, l, c, v = map(_d, (bar.open, bar.high, bar.low, bar.close, bar.volume))
    if min(o, h, l, c) <= ZERO or v < ZERO or h < max(o, l, c) or l > min(o, h, c):
        raise OrderSimError("invalid OHLCV bar")
    return Bar(bar.timestamp, _money(o), _money(h), _money(l), _money(c), _qty(v))


def _triggered(order: Order, bar: Bar) -> bool:
    if order.order_type not in {"STOP", "STOP_LIMIT"}:
        return True
    assert order.stop_price is not None
    return bar.high >= order.stop_price if order.side == "BUY" else bar.low <= order.stop_price


def _fillable(order: Order, bar: Bar, triggered: bool) -> tuple[bool, Decimal]:
    if not triggered:
        return False, ZERO
    if order.order_type in {"MARKET", "STOP"}:
        return True, bar.open
    assert order.limit_price is not None
    if order.side == "BUY" and bar.low <= order.limit_price:
        return True, min(bar.open, order.limit_price)
    if order.side == "SELL" and bar.high >= order.limit_price:
        return True, max(bar.open, order.limit_price)
    return False, ZERO


def _slipped(price: Decimal, side: str, bps: Decimal) -> Decimal:
    delta = bps / Decimal("10000")
    factor = Decimal("1") + delta if side == "BUY" else Decimal("1") - delta
    return _money(price * factor)


def process_bar(
    order: Order,
    bar: Bar,
    bar_index: int,
    policy: ExecutionPolicy | None = None,
) -> tuple[Order, Fill | None]:
    verify_order(order)
    p = policy or ExecutionPolicy()
    b = _validate_bar(bar)

    if order.status not in {"PENDING", "PARTIALLY_FILLED"}:
        return order, None
    if bar_index < order.created_index:
        return order, None
    if order.expire_index is not None and bar_index > order.expire_index:
        return _finalize_order(replace(order, status="EXPIRED")), None

    trig = order.triggered or _triggered(order, b)
    fillable, raw_price = _fillable(order, b, trig)
    if not fillable:
        if order.tif == "IOC":
            return _finalize_order(replace(order, triggered=trig, status="CANCELLED")), None
        if order.tif == "DAY" and order.expire_index is not None and bar_index >= order.expire_index:
            return _finalize_order(replace(order, triggered=trig, status="EXPIRED")), None
        return _finalize_order(replace(order, triggered=trig)), None

    remaining = _qty(order.quantity - order.filled_quantity)
    max_fill = _qty(b.volume * _d(p.participation_rate))
    fill_qty = min(remaining, max_fill)
    if fill_qty <= ZERO:
        return _finalize_order(replace(order, triggered=trig)), None

    price = _slipped(raw_price, order.side, _d(p.slippage_bps))
    prior_value = order.average_fill_price * order.filled_quantity
    new_filled = _qty(order.filled_quantity + fill_qty)
    avg_price = _money((prior_value + price * fill_qty) / new_filled)
    commission = _money(p.commission_per_order) if order.filled_quantity == ZERO else ZERO
    total_commission = _money(order.commission_paid + commission)
    status = "FILLED" if new_filled >= order.quantity else "PARTIALLY_FILLED"

    updated = _finalize_order(replace(
        order,
        status=status,
        filled_quantity=new_filled,
        average_fill_price=avg_price,
        commission_paid=total_commission,
        triggered=trig,
    ))
    fill = Fill(order.order_id, bar_index, fill_qty, price, commission, "")
    fill = replace(fill, fill_hash=_hash(_fill_payload(fill)))
    return updated, fill


def cancel_order(order: Order) -> Order:
    verify_order(order)
    if order.status not in {"PENDING", "PARTIALLY_FILLED"}:
        raise OrderSimError("only active orders can be cancelled")
    return _finalize_order(replace(order, status="CANCELLED"))


def verify_order(order: Order) -> bool:
    if order.status not in {"PENDING", "PARTIALLY_FILLED", "FILLED", "CANCELLED", "EXPIRED"}:
        raise OrderSimError("invalid status")
    if order.quantity <= ZERO or order.filled_quantity < ZERO or order.filled_quantity > order.quantity:
        raise OrderSimError("invalid quantity state")
    if order.status == "FILLED" and order.filled_quantity != order.quantity:
        raise OrderSimError("filled order quantity mismatch")
    if order.status == "PARTIALLY_FILLED" and not (ZERO < order.filled_quantity < order.quantity):
        raise OrderSimError("partial fill quantity mismatch")
    clean = replace(order, order_hash="")
    if order.order_hash != _hash(_order_payload(clean)):
        raise OrderSimError("order hash mismatch")
    return True


def verify_fill(fill: Fill) -> bool:
    if fill.quantity <= ZERO or fill.price <= ZERO or fill.commission < ZERO:
        raise OrderSimError("invalid fill")
    clean = replace(fill, fill_hash="")
    if fill.fill_hash != _hash(_fill_payload(clean)):
        raise OrderSimError("fill hash mismatch")
    return True


def save_order(order: Order, path: str | Path) -> Path:
    verify_order(order)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(_order_payload(order, True), indent=2, sort_keys=True), encoding="utf-8")
    return target


def load_order(path: str | Path) -> Order:
    p = json.loads(Path(path).read_text(encoding="utf-8"))
    order = Order(
        p["order_id"], p["symbol"], p["side"], p["order_type"], _d(p["quantity"]),
        None if p["limit_price"] is None else _d(p["limit_price"]),
        None if p["stop_price"] is None else _d(p["stop_price"]),
        p["tif"], int(p["created_index"]),
        None if p["expire_index"] is None else int(p["expire_index"]),
        p["status"], _d(p["filled_quantity"]), _d(p["average_fill_price"]),
        _d(p["commission_paid"]), bool(p["triggered"]), p["previous_hash"], p["order_hash"]
    )
    verify_order(order)
    return order


MARKET_DATA_API_CALLED = False
ACCOUNT_API_CALLED = False
NETWORK_ACCESSED = False
BROKER_API_CALLED = False
BROKER_ORDER_CREATED = False
ORDER_SUBMITTED = False
LIVE_EXECUTION_AUTHORIZED = False
FUNDS_RESERVED = False
HOLDINGS_RESERVED = False
