from __future__ import annotations

"""
V28.9 Offline Execution Simulator

Features:
- offline order queue
- MARKET / LIMIT / STOP_LIMIT simulation
- DAY / IOC / FOK time-in-force
- partial fills
- VWAP fill calculation
- configurable slippage
- commission calculation
- cancellation and expiration
- deterministic execution reports
- SHA-256 integrity verification
- execution history
- JSON persistence and tamper detection

Safety boundary:
- no network access
- no market/account/broker APIs
- no real order creation/submission
- no live execution
"""

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
import json

VERSION = "28.9"
ZERO = Decimal("0")
ONE = Decimal("1")
SIX = Decimal("0.000001")


class ExecutionError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise ExecutionError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise ExecutionError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(SIX, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _validate_sha256(value: str, field_name: str) -> str:
    digest = value.strip().lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ExecutionError(f"{field_name} must be a SHA-256 hex digest")
    return digest


@dataclass(frozen=True)
class ExecutionPolicy:
    slippage_bps: Decimal = Decimal("5")
    commission_per_share: Decimal = Decimal("0.005")
    minimum_commission: Decimal = Decimal("1.00")
    max_participation_rate: Decimal = Decimal("0.20")

    def __post_init__(self) -> None:
        if _d(self.slippage_bps) < ZERO:
            raise ExecutionError("slippage_bps cannot be negative")
        if _d(self.commission_per_share) < ZERO:
            raise ExecutionError("commission_per_share cannot be negative")
        if _d(self.minimum_commission) < ZERO:
            raise ExecutionError("minimum_commission cannot be negative")
        rate = _d(self.max_participation_rate)
        if rate <= ZERO or rate > ONE:
            raise ExecutionError("max_participation_rate must be within (0,1]")


@dataclass(frozen=True)
class SimulatedOrder:
    order_id: str
    timestamp: str
    symbol: str
    side: str
    order_type: str
    time_in_force: str
    quantity: int
    limit_price: Decimal | None
    stop_price: Decimal | None
    strategy_hash: str
    order_hash: str


@dataclass(frozen=True)
class MarketBar:
    timestamp: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


@dataclass(frozen=True)
class Fill:
    fill_id: str
    order_id: str
    timestamp: str
    quantity: int
    price: Decimal
    notional: Decimal
    commission: Decimal
    fill_hash: str


@dataclass(frozen=True)
class ExecutionReport:
    version: str
    report_id: str
    order: SimulatedOrder
    status: str
    requested_quantity: int
    filled_quantity: int
    remaining_quantity: int
    average_fill_price: Decimal
    total_notional: Decimal
    total_commission: Decimal
    fills: tuple[Fill, ...]
    reason_codes: tuple[str, ...]
    report_hash: str


@dataclass(frozen=True)
class ExecutionHistory:
    version: str
    reports: tuple[ExecutionReport, ...]
    history_hash: str


def _order_payload(order: SimulatedOrder, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "order_id": order.order_id,
        "timestamp": order.timestamp,
        "symbol": order.symbol,
        "side": order.side,
        "order_type": order.order_type,
        "time_in_force": order.time_in_force,
        "quantity": order.quantity,
        "limit_price": None if order.limit_price is None else str(order.limit_price),
        "stop_price": None if order.stop_price is None else str(order.stop_price),
        "strategy_hash": order.strategy_hash,
    }
    if include_hash:
        payload["order_hash"] = order.order_hash
    return payload


def _fill_payload(fill: Fill, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "fill_id": fill.fill_id,
        "order_id": fill.order_id,
        "timestamp": fill.timestamp,
        "quantity": fill.quantity,
        "price": str(fill.price),
        "notional": str(fill.notional),
        "commission": str(fill.commission),
    }
    if include_hash:
        payload["fill_hash"] = fill.fill_hash
    return payload


def _report_payload(report: ExecutionReport, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": report.version,
        "report_id": report.report_id,
        "order": _order_payload(report.order, include_hash=True),
        "status": report.status,
        "requested_quantity": report.requested_quantity,
        "filled_quantity": report.filled_quantity,
        "remaining_quantity": report.remaining_quantity,
        "average_fill_price": str(report.average_fill_price),
        "total_notional": str(report.total_notional),
        "total_commission": str(report.total_commission),
        "fills": [_fill_payload(fill, include_hash=True) for fill in report.fills],
        "reason_codes": list(report.reason_codes),
    }
    if include_hash:
        payload["report_hash"] = report.report_hash
    return payload


def _history_payload(history: ExecutionHistory, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": history.version,
        "reports": [_report_payload(report, include_hash=True) for report in history.reports],
    }
    if include_hash:
        payload["history_hash"] = history.history_hash
    return payload


def create_order(
    *,
    order_id: str,
    timestamp: str,
    symbol: str,
    side: str,
    order_type: str,
    time_in_force: str,
    quantity: int,
    strategy_hash: str,
    limit_price: Any | None = None,
    stop_price: Any | None = None,
) -> SimulatedOrder:
    oid = order_id.strip()
    ts = timestamp.strip()
    sym = symbol.strip().upper()
    side_value = side.strip().upper()
    type_value = order_type.strip().upper()
    tif = time_in_force.strip().upper()

    if not oid or not ts or not sym:
        raise ExecutionError("order_id, timestamp, and symbol are required")
    if side_value not in {"BUY", "SELL"}:
        raise ExecutionError("side must be BUY or SELL")
    if type_value not in {"MARKET", "LIMIT", "STOP_LIMIT"}:
        raise ExecutionError("unsupported order type")
    if tif not in {"DAY", "IOC", "FOK"}:
        raise ExecutionError("unsupported time in force")
    if quantity <= 0:
        raise ExecutionError("quantity must be positive")

    strategy_digest = _validate_sha256(strategy_hash, "strategy_hash")
    limit = None if limit_price is None else _q(limit_price)
    stop = None if stop_price is None else _q(stop_price)

    if type_value == "LIMIT" and limit is None:
        raise ExecutionError("LIMIT order requires limit_price")
    if type_value == "STOP_LIMIT" and (limit is None or stop is None):
        raise ExecutionError("STOP_LIMIT order requires stop_price and limit_price")
    if limit is not None and limit <= ZERO:
        raise ExecutionError("limit_price must be positive")
    if stop is not None and stop <= ZERO:
        raise ExecutionError("stop_price must be positive")

    order = SimulatedOrder(
        order_id=oid,
        timestamp=ts,
        symbol=sym,
        side=side_value,
        order_type=type_value,
        time_in_force=tif,
        quantity=int(quantity),
        limit_price=limit,
        stop_price=stop,
        strategy_hash=strategy_digest,
        order_hash="",
    )
    return replace(order, order_hash=_hash(_order_payload(order)))


def verify_order(order: SimulatedOrder) -> bool:
    _validate_sha256(order.strategy_hash, "strategy_hash")
    if order.side not in {"BUY", "SELL"}:
        raise ExecutionError("invalid order side")
    if order.order_type not in {"MARKET", "LIMIT", "STOP_LIMIT"}:
        raise ExecutionError("invalid order type")
    if order.time_in_force not in {"DAY", "IOC", "FOK"}:
        raise ExecutionError("invalid time in force")
    if order.quantity <= 0:
        raise ExecutionError("invalid order quantity")
    clean = replace(order, order_hash="")
    if order.order_hash != _hash(_order_payload(clean)):
        raise ExecutionError("order hash mismatch")
    return True


def _eligible_price(order: SimulatedOrder, bar: MarketBar) -> Decimal | None:
    open_price = _q(bar.open)
    high = _q(bar.high)
    low = _q(bar.low)
    close = _q(bar.close)

    if min(open_price, high, low, close) <= ZERO:
        raise ExecutionError("market prices must be positive")
    if high < low:
        raise ExecutionError("bar high cannot be below low")
    if bar.volume < 0:
        raise ExecutionError("bar volume cannot be negative")

    if order.order_type == "MARKET":
        return open_price

    if order.order_type == "LIMIT":
        assert order.limit_price is not None
        if order.side == "BUY" and low <= order.limit_price:
            return min(open_price, order.limit_price)
        if order.side == "SELL" and high >= order.limit_price:
            return max(open_price, order.limit_price)
        return None

    assert order.stop_price is not None and order.limit_price is not None
    triggered = (
        high >= order.stop_price if order.side == "BUY"
        else low <= order.stop_price
    )
    if not triggered:
        return None
    if order.side == "BUY" and low <= order.limit_price:
        return min(max(open_price, order.stop_price), order.limit_price)
    if order.side == "SELL" and high >= order.limit_price:
        return max(min(open_price, order.stop_price), order.limit_price)
    return None


def simulate_execution(
    order: SimulatedOrder,
    bars: Iterable[MarketBar],
    policy: ExecutionPolicy | None = None,
) -> ExecutionReport:
    selected = policy or ExecutionPolicy()
    verify_order(order)
    market_bars = tuple(bars)
    if not market_bars:
        raise ExecutionError("at least one market bar is required")
    if len({bar.timestamp for bar in market_bars}) != len(market_bars):
        raise ExecutionError("duplicate market-bar timestamps detected")

    remaining = order.quantity
    fills = []
    reasons = []
    slippage_rate = _d(selected.slippage_bps) / Decimal("10000")

    for bar in sorted(market_bars, key=lambda value: value.timestamp):
        if remaining <= 0:
            break

        eligible = _eligible_price(order, bar)
        if eligible is None:
            continue

        capacity = int(
            Decimal(bar.volume) * _d(selected.max_participation_rate)
        )
        if capacity <= 0:
            continue

        fill_qty = min(remaining, capacity)

        if order.time_in_force == "FOK":
            total_capacity = sum(
                int(Decimal(candidate.volume) * _d(selected.max_participation_rate))
                for candidate in market_bars
                if _eligible_price(order, candidate) is not None
            )
            if total_capacity < order.quantity:
                reasons.append("FOK_NOT_FILLED")
                fills = []
                remaining = order.quantity
                break

        slipped = (
            eligible * (ONE + slippage_rate)
            if order.side == "BUY"
            else eligible * (ONE - slippage_rate)
        )
        price = _q(slipped)
        notional = _q(price * Decimal(fill_qty))
        commission = _q(max(
            _d(selected.minimum_commission),
            _d(selected.commission_per_share) * Decimal(fill_qty),
        ))

        fill_seed = _hash({
            "order_id": order.order_id,
            "timestamp": bar.timestamp,
            "quantity": fill_qty,
            "price": str(price),
            "sequence": len(fills) + 1,
        })
        fill = Fill(
            fill_id=f"FILL-{fill_seed[:16].upper()}",
            order_id=order.order_id,
            timestamp=bar.timestamp,
            quantity=fill_qty,
            price=price,
            notional=notional,
            commission=commission,
            fill_hash="",
        )
        fill = replace(fill, fill_hash=_hash(_fill_payload(fill)))
        fills.append(fill)
        remaining -= fill_qty

        if order.time_in_force == "IOC":
            if remaining > 0:
                reasons.append("IOC_REMAINDER_CANCELLED")
            break

    filled = sum(fill.quantity for fill in fills)
    total_notional = _q(sum((fill.notional for fill in fills), ZERO))
    total_commission = _q(sum((fill.commission for fill in fills), ZERO))
    average = (
        ZERO if filled == 0
        else _q(total_notional / Decimal(filled))
    )

    if filled == order.quantity:
        status = "FILLED"
    elif filled > 0:
        status = "PARTIALLY_FILLED"
        if order.time_in_force == "DAY":
            reasons.append("DAY_EXPIRED_WITH_REMAINDER")
    else:
        status = "CANCELLED" if order.time_in_force in {"IOC", "FOK"} else "EXPIRED"
        if not reasons:
            reasons.append("NO_ELIGIBLE_FILL")

    report_seed = _hash({
        "order_hash": order.order_hash,
        "fill_hashes": [fill.fill_hash for fill in fills],
        "status": status,
        "reasons": sorted(set(reasons)),
    })

    report = ExecutionReport(
        version=VERSION,
        report_id=f"REPORT-{report_seed[:16].upper()}",
        order=order,
        status=status,
        requested_quantity=order.quantity,
        filled_quantity=filled,
        remaining_quantity=order.quantity - filled,
        average_fill_price=average,
        total_notional=total_notional,
        total_commission=total_commission,
        fills=tuple(fills),
        reason_codes=tuple(sorted(set(reasons))),
        report_hash="",
    )
    return replace(report, report_hash=_hash(_report_payload(report)))


def verify_fill(fill: Fill) -> bool:
    if fill.quantity <= 0 or fill.price <= ZERO:
        raise ExecutionError("invalid fill")
    if fill.notional != _q(fill.price * Decimal(fill.quantity)):
        raise ExecutionError("fill notional mismatch")
    clean = replace(fill, fill_hash="")
    if fill.fill_hash != _hash(_fill_payload(clean)):
        raise ExecutionError("fill hash mismatch")
    return True


def verify_report(report: ExecutionReport) -> bool:
    if report.version != VERSION:
        raise ExecutionError("unsupported execution version")
    verify_order(report.order)
    for fill in report.fills:
        verify_fill(fill)
    if report.filled_quantity != sum(fill.quantity for fill in report.fills):
        raise ExecutionError("filled quantity mismatch")
    if report.remaining_quantity != report.requested_quantity - report.filled_quantity:
        raise ExecutionError("remaining quantity mismatch")
    if report.total_notional != sum((fill.notional for fill in report.fills), ZERO):
        raise ExecutionError("total notional mismatch")
    if report.total_commission != sum((fill.commission for fill in report.fills), ZERO):
        raise ExecutionError("total commission mismatch")
    if report.filled_quantity == 0 and report.average_fill_price != ZERO:
        raise ExecutionError("zero-fill report must have zero average price")
    if report.status not in {"FILLED", "PARTIALLY_FILLED", "CANCELLED", "EXPIRED"}:
        raise ExecutionError("invalid execution status")
    clean = replace(report, report_hash="")
    if report.report_hash != _hash(_report_payload(clean)):
        raise ExecutionError("execution report hash mismatch")
    return True


def create_history(reports: Iterable[ExecutionReport]) -> ExecutionHistory:
    items = tuple(reports)
    if not items:
        raise ExecutionError("execution history cannot be empty")
    if len({report.report_id for report in items}) != len(items):
        raise ExecutionError("duplicate report IDs detected")
    for report in items:
        verify_report(report)
    history = ExecutionHistory(VERSION, items, "")
    return replace(history, history_hash=_hash(_history_payload(history)))


def verify_history(history: ExecutionHistory) -> bool:
    if history.version != VERSION:
        raise ExecutionError("unsupported history version")
    if not history.reports:
        raise ExecutionError("execution history cannot be empty")
    if len({report.report_id for report in history.reports}) != len(history.reports):
        raise ExecutionError("duplicate report IDs detected")
    for report in history.reports:
        verify_report(report)
    clean = replace(history, history_hash="")
    if history.history_hash != _hash(_history_payload(clean)):
        raise ExecutionError("history hash mismatch")
    return True


def save_history(history: ExecutionHistory, path: str | Path) -> Path:
    verify_history(history)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_history_payload(history, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_history(path: str | Path) -> ExecutionHistory:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    reports = []
    for item in payload["reports"]:
        order_data = item["order"]
        order = SimulatedOrder(
            order_id=order_data["order_id"],
            timestamp=order_data["timestamp"],
            symbol=order_data["symbol"],
            side=order_data["side"],
            order_type=order_data["order_type"],
            time_in_force=order_data["time_in_force"],
            quantity=int(order_data["quantity"]),
            limit_price=None if order_data["limit_price"] is None else _d(order_data["limit_price"]),
            stop_price=None if order_data["stop_price"] is None else _d(order_data["stop_price"]),
            strategy_hash=order_data["strategy_hash"],
            order_hash=order_data["order_hash"],
        )
        fills = tuple(
            Fill(
                fill_id=fill["fill_id"],
                order_id=fill["order_id"],
                timestamp=fill["timestamp"],
                quantity=int(fill["quantity"]),
                price=_d(fill["price"]),
                notional=_d(fill["notional"]),
                commission=_d(fill["commission"]),
                fill_hash=fill["fill_hash"],
            )
            for fill in item["fills"]
        )
        reports.append(ExecutionReport(
            version=item["version"],
            report_id=item["report_id"],
            order=order,
            status=item["status"],
            requested_quantity=int(item["requested_quantity"]),
            filled_quantity=int(item["filled_quantity"]),
            remaining_quantity=int(item["remaining_quantity"]),
            average_fill_price=_d(item["average_fill_price"]),
            total_notional=_d(item["total_notional"]),
            total_commission=_d(item["total_commission"]),
            fills=fills,
            reason_codes=tuple(item["reason_codes"]),
            report_hash=item["report_hash"],
        ))
    history = ExecutionHistory(
        version=payload["version"],
        reports=tuple(reports),
        history_hash=payload["history_hash"],
    )
    verify_history(history)
    return history


MARKET_DATA_API_CALLED = False
ACCOUNT_API_CALLED = False
NETWORK_ACCESSED = False
BROKER_API_CALLED = False
BROKER_ORDER_CREATED = False
ORDER_SUBMITTED = False
LIVE_EXECUTION_AUTHORIZED = False
FUNDS_RESERVED = False
HOLDINGS_RESERVED = False
