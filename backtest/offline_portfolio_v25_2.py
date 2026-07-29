from __future__ import annotations

from dataclasses import dataclass, asdict, replace
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Mapping, Any
import json

VERSION = "25.2"
CENT = Decimal("0.01")
QTY = Decimal("0.000001")
ZERO = Decimal("0")


class PortfolioError(ValueError):
    pass


def dec(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise PortfolioError(f"invalid numeric value: {value!r}") from exc
    if not result.is_finite():
        raise PortfolioError("numeric value must be finite")
    return result


def money(value: Any) -> Decimal:
    return dec(value).quantize(CENT, rounding=ROUND_HALF_UP)


def quantity(value: Any) -> Decimal:
    return dec(value).quantize(QTY, rounding=ROUND_HALF_UP)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def utc_timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PortfolioError("timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise PortfolioError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def symbol_code(value: str) -> str:
    result = value.strip().upper()
    if not result or len(result) > 15 or not all(c.isalnum() or c in ".-" for c in result):
        raise PortfolioError("invalid symbol")
    return result


@dataclass(frozen=True)
class PortfolioPolicy:
    starting_cash: Decimal = Decimal("100000.00")
    max_position_pct: Decimal = Decimal("0.25")
    max_gross_exposure_pct: Decimal = Decimal("0.95")
    min_cash_reserve_pct: Decimal = Decimal("0.05")
    allow_fractional: bool = True
    allow_short: bool = False
    commission: Decimal = Decimal("0.00")
    slippage_bps: Decimal = Decimal("0.00")

    def __post_init__(self) -> None:
        if money(self.starting_cash) <= ZERO:
            raise PortfolioError("starting cash must be positive")
        for name in ("max_position_pct", "max_gross_exposure_pct", "min_cash_reserve_pct"):
            value = dec(getattr(self, name))
            if value < ZERO or value > Decimal("1"):
                raise PortfolioError(f"{name} must be between 0 and 1")
        if dec(self.max_position_pct) > dec(self.max_gross_exposure_pct):
            raise PortfolioError("position limit exceeds gross exposure limit")
        if dec(self.commission) < ZERO or dec(self.slippage_bps) < ZERO:
            raise PortfolioError("fees cannot be negative")


@dataclass(frozen=True)
class Position:
    symbol: str
    quantity: Decimal
    average_cost: Decimal
    market_price: Decimal
    realized_pnl: Decimal = ZERO

    @property
    def market_value(self) -> Decimal:
        return money(self.quantity * self.market_price)

    @property
    def unrealized_pnl(self) -> Decimal:
        return money((self.market_price - self.average_cost) * self.quantity)


@dataclass(frozen=True)
class PortfolioEvent:
    sequence: int
    timestamp: str
    kind: str
    symbol: str
    quantity: Decimal
    price: Decimal
    cash_after: Decimal
    previous_hash: str
    event_hash: str


@dataclass(frozen=True)
class PortfolioSnapshot:
    version: str
    policy: PortfolioPolicy
    cash: Decimal
    positions: tuple[Position, ...]
    events: tuple[PortfolioEvent, ...]
    snapshot_hash: str

    @property
    def market_value(self) -> Decimal:
        return money(sum((p.market_value for p in self.positions), ZERO))

    @property
    def equity(self) -> Decimal:
        return money(self.cash + self.market_value)

    @property
    def unrealized_pnl(self) -> Decimal:
        return money(sum((p.unrealized_pnl for p in self.positions), ZERO))


def policy_payload(policy: PortfolioPolicy) -> dict[str, Any]:
    raw = asdict(policy)
    return {key: str(value) if isinstance(value, Decimal) else value for key, value in raw.items()}


def position_payload(position: Position) -> dict[str, str]:
    return {
        "symbol": position.symbol,
        "quantity": str(position.quantity),
        "average_cost": str(position.average_cost),
        "market_price": str(position.market_price),
        "realized_pnl": str(position.realized_pnl),
    }


def event_core(event: PortfolioEvent) -> dict[str, Any]:
    return {
        "sequence": event.sequence,
        "timestamp": event.timestamp,
        "kind": event.kind,
        "symbol": event.symbol,
        "quantity": str(event.quantity),
        "price": str(event.price),
        "cash_after": str(event.cash_after),
        "previous_hash": event.previous_hash,
    }


def snapshot_payload(snapshot: PortfolioSnapshot, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": snapshot.version,
        "policy": policy_payload(snapshot.policy),
        "cash": str(snapshot.cash),
        "positions": [position_payload(p) for p in snapshot.positions],
        "events": [{**event_core(e), "event_hash": e.event_hash} for e in snapshot.events],
    }
    if include_hash:
        payload["snapshot_hash"] = snapshot.snapshot_hash
    return payload


def finalize(snapshot: PortfolioSnapshot) -> PortfolioSnapshot:
    clean = replace(snapshot, snapshot_hash="")
    return replace(clean, snapshot_hash=digest(snapshot_payload(clean)))


def new_portfolio(policy: PortfolioPolicy | None = None) -> PortfolioSnapshot:
    selected = policy or PortfolioPolicy()
    return finalize(PortfolioSnapshot(
        version=VERSION,
        policy=selected,
        cash=money(selected.starting_cash),
        positions=(),
        events=(),
        snapshot_hash="",
    ))


def positions_by_symbol(snapshot: PortfolioSnapshot) -> dict[str, Position]:
    return {p.symbol: p for p in snapshot.positions}


def append_event(
    snapshot: PortfolioSnapshot,
    kind: str,
    symbol: str,
    qty: Decimal,
    price: Decimal,
    cash_after: Decimal,
    timestamp: str | None,
) -> tuple[PortfolioEvent, ...]:
    ts = utc_timestamp(timestamp)
    if snapshot.events and ts <= snapshot.events[-1].timestamp:
        raise PortfolioError("event timestamps must be strictly increasing")
    previous = snapshot.events[-1].event_hash if snapshot.events else "GENESIS"
    event = PortfolioEvent(
        sequence=len(snapshot.events) + 1,
        timestamp=ts,
        kind=kind,
        symbol=symbol,
        quantity=qty,
        price=price,
        cash_after=cash_after,
        previous_hash=previous,
        event_hash="",
    )
    event = replace(event, event_hash=digest(event_core(event)))
    return snapshot.events + (event,)


def fill_price(raw_price: Decimal, side: str, bps: Decimal) -> Decimal:
    adjustment = bps / Decimal("10000")
    factor = Decimal("1") + adjustment if side == "BUY" else Decimal("1") - adjustment
    return money(raw_price * factor)


def buy(snapshot: PortfolioSnapshot, symbol: str, qty: Any, price: Any, *, timestamp: str | None = None) -> PortfolioSnapshot:
    verify_snapshot(snapshot)
    sym = symbol_code(symbol)
    amount = quantity(qty)
    px = money(price)
    if amount <= ZERO or px <= ZERO:
        raise PortfolioError("quantity and price must be positive")
    if not snapshot.policy.allow_fractional and amount != amount.to_integral_value():
        raise PortfolioError("fractional quantity disabled")

    execution = fill_price(px, "BUY", dec(snapshot.policy.slippage_bps))
    fee = money(snapshot.policy.commission)
    cost = money(amount * execution + fee)
    cash = money(snapshot.cash - cost)
    if cash < money(snapshot.equity * dec(snapshot.policy.min_cash_reserve_pct)):
        raise PortfolioError("minimum cash reserve violated")

    items = positions_by_symbol(snapshot)
    old = items.get(sym)
    old_qty = old.quantity if old else ZERO
    old_cost = old.average_cost if old else ZERO
    new_qty = quantity(old_qty + amount)
    avg = money((old_qty * old_cost + amount * execution + fee) / new_qty)
    realized = old.realized_pnl if old else ZERO
    items[sym] = Position(sym, new_qty, avg, execution, realized)

    projected_market = money(sum((p.market_value for p in items.values()), ZERO))
    projected_equity = money(projected_market + cash)
    if items[sym].market_value / projected_equity > dec(snapshot.policy.max_position_pct):
        raise PortfolioError("maximum position allocation exceeded")
    if projected_market / projected_equity > dec(snapshot.policy.max_gross_exposure_pct):
        raise PortfolioError("maximum gross exposure exceeded")

    updated = replace(
        snapshot,
        cash=cash,
        positions=tuple(sorted(items.values(), key=lambda p: p.symbol)),
        events=append_event(snapshot, "BUY", sym, amount, execution, cash, timestamp),
        snapshot_hash="",
    )
    return finalize(updated)


def sell(snapshot: PortfolioSnapshot, symbol: str, qty: Any, price: Any, *, timestamp: str | None = None) -> PortfolioSnapshot:
    verify_snapshot(snapshot)
    sym = symbol_code(symbol)
    amount = quantity(qty)
    px = money(price)
    if amount <= ZERO or px <= ZERO:
        raise PortfolioError("quantity and price must be positive")

    items = positions_by_symbol(snapshot)
    old = items.get(sym)
    if old is None:
        raise PortfolioError("position does not exist")
    if not snapshot.policy.allow_short and amount > old.quantity:
        raise PortfolioError("short selling disabled")

    execution = fill_price(px, "SELL", dec(snapshot.policy.slippage_bps))
    fee = money(snapshot.policy.commission)
    proceeds = money(amount * execution - fee)
    cash = money(snapshot.cash + proceeds)
    remaining = quantity(old.quantity - amount)
    realized = money(old.realized_pnl + (execution - old.average_cost) * amount - fee)

    if remaining == ZERO:
        del items[sym]
    else:
        items[sym] = Position(sym, remaining, old.average_cost, execution, realized)

    updated = replace(
        snapshot,
        cash=cash,
        positions=tuple(sorted(items.values(), key=lambda p: p.symbol)),
        events=append_event(snapshot, "SELL", sym, amount, execution, cash, timestamp),
        snapshot_hash="",
    )
    return finalize(updated)


def mark_to_market(snapshot: PortfolioSnapshot, prices: Mapping[str, Any], *, timestamp: str | None = None) -> PortfolioSnapshot:
    verify_snapshot(snapshot)
    normalized = {symbol_code(k): money(v) for k, v in prices.items()}
    if any(v <= ZERO for v in normalized.values()):
        raise PortfolioError("market prices must be positive")
    items = positions_by_symbol(snapshot)
    changed = False
    for sym, old in tuple(items.items()):
        if sym in normalized:
            items[sym] = replace(old, market_price=normalized[sym])
            changed = True
    if not changed:
        raise PortfolioError("no matching prices supplied")

    updated = replace(
        snapshot,
        positions=tuple(sorted(items.values(), key=lambda p: p.symbol)),
        events=append_event(snapshot, "MARK", "*", ZERO, ZERO, snapshot.cash, timestamp),
        snapshot_hash="",
    )
    return finalize(updated)


def allocation(snapshot: PortfolioSnapshot) -> dict[str, Decimal]:
    verify_snapshot(snapshot)
    if snapshot.equity <= ZERO:
        raise PortfolioError("equity must be positive")
    result = {
        p.symbol: (p.market_value / snapshot.equity).quantize(Decimal("0.0001"))
        for p in snapshot.positions
    }
    result["CASH"] = (snapshot.cash / snapshot.equity).quantize(Decimal("0.0001"))
    return result


def verify_snapshot(snapshot: PortfolioSnapshot) -> bool:
    if snapshot.version != VERSION:
        raise PortfolioError("unsupported version")
    if snapshot.cash < ZERO:
        raise PortfolioError("negative cash")
    if snapshot.positions != tuple(sorted(snapshot.positions, key=lambda p: p.symbol)):
        raise PortfolioError("positions are not sorted")
    if len({p.symbol for p in snapshot.positions}) != len(snapshot.positions):
        raise PortfolioError("duplicate positions")
    for p in snapshot.positions:
        if p.quantity <= ZERO or p.average_cost <= ZERO or p.market_price <= ZERO:
            raise PortfolioError("invalid position")

    previous = "GENESIS"
    prior_time = ""
    for expected, event in enumerate(snapshot.events, 1):
        if event.sequence != expected or event.previous_hash != previous:
            raise PortfolioError("broken event chain")
        if prior_time and event.timestamp <= prior_time:
            raise PortfolioError("invalid event time order")
        if event.event_hash != digest(event_core(replace(event, event_hash=""))):
            raise PortfolioError("event hash mismatch")
        previous = event.event_hash
        prior_time = event.timestamp

    clean = replace(snapshot, snapshot_hash="")
    if snapshot.snapshot_hash != digest(snapshot_payload(clean)):
        raise PortfolioError("snapshot hash mismatch")
    return True


def save_snapshot(snapshot: PortfolioSnapshot, path: str | Path) -> Path:
    verify_snapshot(snapshot)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(snapshot_payload(snapshot, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_snapshot(path: str | Path) -> PortfolioSnapshot:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    p = raw["policy"]
    policy = PortfolioPolicy(
        starting_cash=dec(p["starting_cash"]),
        max_position_pct=dec(p["max_position_pct"]),
        max_gross_exposure_pct=dec(p["max_gross_exposure_pct"]),
        min_cash_reserve_pct=dec(p["min_cash_reserve_pct"]),
        allow_fractional=bool(p["allow_fractional"]),
        allow_short=bool(p["allow_short"]),
        commission=dec(p["commission"]),
        slippage_bps=dec(p["slippage_bps"]),
    )
    positions = tuple(Position(
        x["symbol"], dec(x["quantity"]), dec(x["average_cost"]),
        dec(x["market_price"]), dec(x["realized_pnl"])
    ) for x in raw["positions"])
    events = tuple(PortfolioEvent(
        int(x["sequence"]), x["timestamp"], x["kind"], x["symbol"],
        dec(x["quantity"]), dec(x["price"]), dec(x["cash_after"]),
        x["previous_hash"], x["event_hash"]
    ) for x in raw["events"])
    snapshot = PortfolioSnapshot(
        raw["version"], policy, dec(raw["cash"]), positions, events, raw["snapshot_hash"]
    )
    verify_snapshot(snapshot)
    return snapshot


MARKET_DATA_API_CALLED = False
ACCOUNT_API_CALLED = False
NETWORK_ACCESSED = False
BROKER_API_CALLED = False
BROKER_ORDER_CREATED = False
ORDER_SUBMITTED = False
LIVE_EXECUTION_AUTHORIZED = False
FUNDS_RESERVED = False
HOLDINGS_RESERVED = False
