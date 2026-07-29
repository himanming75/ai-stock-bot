from __future__ import annotations

"""
V25.3 Offline Risk Manager

Deterministic, offline-only risk controls for position sizing, stop planning,
daily loss limits, sector exposure, concurrent positions, and trade approval.

Safety boundary:
- no network access
- no broker/account APIs
- no live order creation/submission
- no external fund or holding reservation
"""

from dataclasses import asdict, dataclass, replace
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping
import json

VERSION = "25.3"
ZERO = Decimal("0")
CENT = Decimal("0.01")
QTY_STEP = Decimal("0.000001")


class RiskError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise RiskError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise RiskError("decimal value must be finite")
    return result


def _money(value: Any) -> Decimal:
    return _d(value).quantize(CENT, rounding=ROUND_HALF_UP)


def _qty(value: Any) -> Decimal:
    return _d(value).quantize(QTY_STEP, rounding=ROUND_DOWN)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _symbol(value: str) -> str:
    result = value.strip().upper()
    if not result or len(result) > 15 or not all(c.isalnum() or c in ".-" for c in result):
        raise RiskError("invalid symbol")
    return result


@dataclass(frozen=True)
class RiskPolicy:
    risk_per_trade_pct: Decimal = Decimal("0.01")
    max_daily_loss_pct: Decimal = Decimal("0.03")
    max_position_pct: Decimal = Decimal("0.20")
    max_sector_pct: Decimal = Decimal("0.35")
    max_open_positions: int = 8
    stop_atr_multiple: Decimal = Decimal("2.0")
    take_profit_r_multiple: Decimal = Decimal("2.0")
    trailing_stop_atr_multiple: Decimal = Decimal("2.5")
    break_even_r_multiple: Decimal = Decimal("1.0")
    min_reward_risk: Decimal = Decimal("1.5")
    allow_fractional: bool = True

    def __post_init__(self) -> None:
        for name in (
            "risk_per_trade_pct", "max_daily_loss_pct",
            "max_position_pct", "max_sector_pct",
        ):
            value = _d(getattr(self, name))
            if value <= ZERO or value > Decimal("1"):
                raise RiskError(f"{name} must be greater than 0 and at most 1")
        for name in (
            "stop_atr_multiple", "take_profit_r_multiple",
            "trailing_stop_atr_multiple", "break_even_r_multiple",
            "min_reward_risk",
        ):
            if _d(getattr(self, name)) <= ZERO:
                raise RiskError(f"{name} must be positive")
        if self.max_open_positions <= 0:
            raise RiskError("max_open_positions must be positive")


@dataclass(frozen=True)
class PositionRisk:
    symbol: str
    sector: str
    quantity: Decimal
    entry_price: Decimal
    market_price: Decimal
    stop_price: Decimal

    @property
    def market_value(self) -> Decimal:
        return _money(self.quantity * self.market_price)

    @property
    def open_risk(self) -> Decimal:
        return _money(max(self.entry_price - self.stop_price, ZERO) * self.quantity)


@dataclass(frozen=True)
class RiskRequest:
    symbol: str
    sector: str
    entry_price: Decimal
    atr: Decimal
    account_equity: Decimal
    available_cash: Decimal
    current_daily_pnl: Decimal
    open_positions: tuple[PositionRisk, ...] = ()
    requested_quantity: Decimal | None = None


@dataclass(frozen=True)
class RiskDecision:
    version: str
    approved: bool
    symbol: str
    sector: str
    quantity: Decimal
    entry_price: Decimal
    stop_price: Decimal
    take_profit_price: Decimal
    trailing_stop_distance: Decimal
    break_even_trigger: Decimal
    risk_amount: Decimal
    reward_amount: Decimal
    reward_risk_ratio: Decimal
    projected_position_pct: Decimal
    projected_sector_pct: Decimal
    reason_codes: tuple[str, ...]
    input_hash: str
    decision_hash: str


def _position_payload(position: PositionRisk) -> dict[str, str]:
    return {
        "symbol": position.symbol,
        "sector": position.sector,
        "quantity": str(position.quantity),
        "entry_price": str(position.entry_price),
        "market_price": str(position.market_price),
        "stop_price": str(position.stop_price),
    }


def _request_payload(request: RiskRequest) -> dict[str, Any]:
    return {
        "symbol": request.symbol,
        "sector": request.sector,
        "entry_price": str(request.entry_price),
        "atr": str(request.atr),
        "account_equity": str(request.account_equity),
        "available_cash": str(request.available_cash),
        "current_daily_pnl": str(request.current_daily_pnl),
        "open_positions": [_position_payload(p) for p in request.open_positions],
        "requested_quantity": None if request.requested_quantity is None else str(request.requested_quantity),
    }


def _policy_payload(policy: RiskPolicy) -> dict[str, Any]:
    raw = asdict(policy)
    return {k: str(v) if isinstance(v, Decimal) else v for k, v in raw.items()}


def _decision_payload(decision: RiskDecision, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": decision.version,
        "approved": decision.approved,
        "symbol": decision.symbol,
        "sector": decision.sector,
        "quantity": str(decision.quantity),
        "entry_price": str(decision.entry_price),
        "stop_price": str(decision.stop_price),
        "take_profit_price": str(decision.take_profit_price),
        "trailing_stop_distance": str(decision.trailing_stop_distance),
        "break_even_trigger": str(decision.break_even_trigger),
        "risk_amount": str(decision.risk_amount),
        "reward_amount": str(decision.reward_amount),
        "reward_risk_ratio": str(decision.reward_risk_ratio),
        "projected_position_pct": str(decision.projected_position_pct),
        "projected_sector_pct": str(decision.projected_sector_pct),
        "reason_codes": list(decision.reason_codes),
        "input_hash": decision.input_hash,
    }
    if include_hash:
        payload["decision_hash"] = decision.decision_hash
    return payload


def _normalize_position(position: PositionRisk) -> PositionRisk:
    symbol = _symbol(position.symbol)
    sector = position.sector.strip().upper()
    if not sector:
        raise RiskError("sector cannot be empty")
    quantity = _qty(position.quantity)
    entry = _money(position.entry_price)
    market = _money(position.market_price)
    stop = _money(position.stop_price)
    if quantity <= ZERO or entry <= ZERO or market <= ZERO or stop < ZERO:
        raise RiskError("invalid open position values")
    return PositionRisk(symbol, sector, quantity, entry, market, stop)


def _normalize_request(request: RiskRequest) -> RiskRequest:
    symbol = _symbol(request.symbol)
    sector = request.sector.strip().upper()
    if not sector:
        raise RiskError("sector cannot be empty")

    entry = _money(request.entry_price)
    atr = _money(request.atr)
    equity = _money(request.account_equity)
    cash = _money(request.available_cash)
    daily_pnl = _money(request.current_daily_pnl)
    requested = None if request.requested_quantity is None else _qty(request.requested_quantity)
    positions = tuple(_normalize_position(p) for p in request.open_positions)

    if entry <= ZERO or atr <= ZERO or equity <= ZERO or cash < ZERO:
        raise RiskError("entry, ATR, and equity must be positive; cash cannot be negative")
    if requested is not None and requested <= ZERO:
        raise RiskError("requested quantity must be positive")
    if len({p.symbol for p in positions}) != len(positions):
        raise RiskError("duplicate open position symbols")

    return RiskRequest(
        symbol, sector, entry, atr, equity, cash, daily_pnl, positions, requested
    )


def calculate_position_size(
    account_equity: Any,
    risk_per_trade_pct: Any,
    entry_price: Any,
    stop_price: Any,
    *,
    allow_fractional: bool = True,
) -> Decimal:
    equity = _money(account_equity)
    risk_pct = _d(risk_per_trade_pct)
    entry = _money(entry_price)
    stop = _money(stop_price)
    per_share_risk = entry - stop

    if equity <= ZERO or risk_pct <= ZERO or risk_pct > Decimal("1"):
        raise RiskError("invalid equity or risk percentage")
    if entry <= ZERO or stop < ZERO or per_share_risk <= ZERO:
        raise RiskError("stop must be below entry for a long position")

    raw = (equity * risk_pct) / per_share_risk
    if allow_fractional:
        return _qty(raw)
    return raw.to_integral_value(rounding=ROUND_DOWN)


def evaluate_trade(request: RiskRequest, policy: RiskPolicy | None = None) -> RiskDecision:
    selected = policy or RiskPolicy()
    req = _normalize_request(request)

    stop_distance = _money(req.atr * _d(selected.stop_atr_multiple))
    stop_price = _money(req.entry_price - stop_distance)
    take_profit_price = _money(
        req.entry_price + stop_distance * _d(selected.take_profit_r_multiple)
    )
    trailing_distance = _money(req.atr * _d(selected.trailing_stop_atr_multiple))
    break_even_trigger = _money(
        req.entry_price + stop_distance * _d(selected.break_even_r_multiple)
    )

    reasons: list[str] = []
    if stop_price <= ZERO:
        reasons.append("INVALID_STOP")

    daily_loss_limit = _money(req.account_equity * _d(selected.max_daily_loss_pct))
    if req.current_daily_pnl <= -daily_loss_limit:
        reasons.append("DAILY_LOSS_LIMIT")

    existing_symbols = {p.symbol for p in req.open_positions}
    if req.symbol not in existing_symbols and len(req.open_positions) >= selected.max_open_positions:
        reasons.append("MAX_OPEN_POSITIONS")

    if stop_price > ZERO:
        calculated_qty = calculate_position_size(
            req.account_equity,
            selected.risk_per_trade_pct,
            req.entry_price,
            stop_price,
            allow_fractional=selected.allow_fractional,
        )
    else:
        calculated_qty = ZERO

    qty = calculated_qty
    if req.requested_quantity is not None:
        qty = min(qty, req.requested_quantity)

    affordable_qty = _qty(req.available_cash / req.entry_price)
    qty = min(qty, affordable_qty)

    max_position_value = _money(req.account_equity * _d(selected.max_position_pct))
    position_limit_qty = _qty(max_position_value / req.entry_price)
    qty = min(qty, position_limit_qty)

    if not selected.allow_fractional:
        qty = qty.to_integral_value(rounding=ROUND_DOWN)

    if qty <= ZERO:
        reasons.append("ZERO_QUANTITY")

    proposed_value = _money(qty * req.entry_price)
    existing_sector_value = _money(sum(
        (p.market_value for p in req.open_positions if p.sector == req.sector),
        ZERO,
    ))
    projected_position_pct = (
        (proposed_value / req.account_equity).quantize(Decimal("0.0001"))
        if req.account_equity else Decimal("1")
    )
    projected_sector_pct = (
        ((existing_sector_value + proposed_value) / req.account_equity).quantize(Decimal("0.0001"))
        if req.account_equity else Decimal("1")
    )

    if projected_position_pct > _d(selected.max_position_pct):
        reasons.append("MAX_POSITION_PCT")
    if projected_sector_pct > _d(selected.max_sector_pct):
        reasons.append("MAX_SECTOR_PCT")

    risk_amount = _money(max(req.entry_price - stop_price, ZERO) * qty)
    reward_amount = _money(max(take_profit_price - req.entry_price, ZERO) * qty)
    reward_risk_ratio = (
        (reward_amount / risk_amount).quantize(Decimal("0.0001"))
        if risk_amount > ZERO else ZERO
    )
    if reward_risk_ratio < _d(selected.min_reward_risk):
        reasons.append("MIN_REWARD_RISK")

    approved = not reasons
    input_hash = _hash({
        "request": _request_payload(req),
        "policy": _policy_payload(selected),
    })

    decision = RiskDecision(
        version=VERSION,
        approved=approved,
        symbol=req.symbol,
        sector=req.sector,
        quantity=qty,
        entry_price=req.entry_price,
        stop_price=stop_price,
        take_profit_price=take_profit_price,
        trailing_stop_distance=trailing_distance,
        break_even_trigger=break_even_trigger,
        risk_amount=risk_amount,
        reward_amount=reward_amount,
        reward_risk_ratio=reward_risk_ratio,
        projected_position_pct=projected_position_pct,
        projected_sector_pct=projected_sector_pct,
        reason_codes=tuple(sorted(set(reasons))),
        input_hash=input_hash,
        decision_hash="",
    )
    return replace(decision, decision_hash=_hash(_decision_payload(decision)))


def update_protective_stop(
    entry_price: Any,
    current_price: Any,
    current_stop: Any,
    atr: Any,
    *,
    trailing_atr_multiple: Any,
    break_even_r_multiple: Any,
    initial_risk_per_share: Any,
) -> Decimal:
    entry = _money(entry_price)
    current = _money(current_price)
    stop = _money(current_stop)
    atr_value = _money(atr)
    trailing_multiple = _d(trailing_atr_multiple)
    break_even_multiple = _d(break_even_r_multiple)
    initial_risk = _money(initial_risk_per_share)

    if min(entry, current, atr_value, trailing_multiple, break_even_multiple, initial_risk) <= ZERO:
        raise RiskError("protective stop inputs must be positive")
    if stop < ZERO:
        raise RiskError("current stop cannot be negative")

    candidate = stop
    trailing_candidate = _money(current - atr_value * trailing_multiple)
    if trailing_candidate > candidate:
        candidate = trailing_candidate

    break_even_trigger = _money(entry + initial_risk * break_even_multiple)
    if current >= break_even_trigger and entry > candidate:
        candidate = entry

    return min(candidate, current)


def verify_decision(decision: RiskDecision) -> bool:
    if decision.version != VERSION:
        raise RiskError("unsupported decision version")
    if decision.quantity < ZERO:
        raise RiskError("quantity cannot be negative")
    if decision.entry_price <= ZERO:
        raise RiskError("entry price must be positive")
    if decision.approved and decision.reason_codes:
        raise RiskError("approved decision cannot contain rejection reasons")
    if not decision.approved and not decision.reason_codes:
        raise RiskError("rejected decision must contain reasons")

    clean = replace(decision, decision_hash="")
    expected = _hash(_decision_payload(clean))
    if decision.decision_hash != expected:
        raise RiskError("decision hash mismatch")
    return True


def save_decision(decision: RiskDecision, path: str | Path) -> Path:
    verify_decision(decision)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_decision_payload(decision, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_decision(path: str | Path) -> RiskDecision:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    decision = RiskDecision(
        version=payload["version"],
        approved=bool(payload["approved"]),
        symbol=payload["symbol"],
        sector=payload["sector"],
        quantity=_d(payload["quantity"]),
        entry_price=_d(payload["entry_price"]),
        stop_price=_d(payload["stop_price"]),
        take_profit_price=_d(payload["take_profit_price"]),
        trailing_stop_distance=_d(payload["trailing_stop_distance"]),
        break_even_trigger=_d(payload["break_even_trigger"]),
        risk_amount=_d(payload["risk_amount"]),
        reward_amount=_d(payload["reward_amount"]),
        reward_risk_ratio=_d(payload["reward_risk_ratio"]),
        projected_position_pct=_d(payload["projected_position_pct"]),
        projected_sector_pct=_d(payload["projected_sector_pct"]),
        reason_codes=tuple(payload["reason_codes"]),
        input_hash=payload["input_hash"],
        decision_hash=payload["decision_hash"],
    )
    verify_decision(decision)
    return decision


MARKET_DATA_API_CALLED = False
ACCOUNT_API_CALLED = False
NETWORK_ACCESSED = False
BROKER_API_CALLED = False
BROKER_ORDER_CREATED = False
ORDER_SUBMITTED = False
LIVE_EXECUTION_AUTHORIZED = False
FUNDS_RESERVED = False
HOLDINGS_RESERVED = False
