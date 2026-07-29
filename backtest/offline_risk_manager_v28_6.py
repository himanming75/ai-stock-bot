from __future__ import annotations

"""
V28.6 Offline Risk Management Engine

Features:
- daily and weekly loss limits
- maximum drawdown limit
- maximum open-position count
- symbol and sector exposure limits
- portfolio heat limit
- correlation-risk limit
- Kelly-fraction cap
- consecutive-loss circuit breaker
- cooldown calculation
- emergency-stop override
- deterministic risk approval
- SHA-256 integrity verification
- risk history
- JSON persistence and tamper detection

Safety boundary:
- no network access
- no market/account/broker APIs
- no order creation/submission
- no live execution
"""

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
import json

VERSION = "28.6"
ZERO = Decimal("0")
ONE = Decimal("1")
SIX = Decimal("0.000001")


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


def _q(value: Any) -> Decimal:
    return _d(value).quantize(SIX, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RiskPolicy:
    max_daily_loss_pct: Decimal = Decimal("2.0")
    max_weekly_loss_pct: Decimal = Decimal("5.0")
    max_drawdown_pct: Decimal = Decimal("12.0")
    max_open_positions: int = 10
    max_symbol_exposure: Decimal = Decimal("0.15")
    max_sector_exposure: Decimal = Decimal("0.40")
    max_portfolio_heat: Decimal = Decimal("0.06")
    max_correlation: Decimal = Decimal("0.90")
    max_kelly_fraction: Decimal = Decimal("0.20")
    max_consecutive_losses: int = 4
    cooldown_minutes: int = 30
    emergency_stop_drawdown_pct: Decimal = Decimal("20.0")

    def __post_init__(self) -> None:
        for name in (
            "max_daily_loss_pct",
            "max_weekly_loss_pct",
            "max_drawdown_pct",
            "emergency_stop_drawdown_pct",
        ):
            if _d(getattr(self, name)) <= ZERO:
                raise RiskError(f"{name} must be positive")
        for name in (
            "max_symbol_exposure",
            "max_sector_exposure",
            "max_portfolio_heat",
            "max_correlation",
            "max_kelly_fraction",
        ):
            value = _d(getattr(self, name))
            if value <= ZERO or value > ONE:
                raise RiskError(f"{name} must be within (0,1]")
        if self.max_open_positions <= 0:
            raise RiskError("max_open_positions must be positive")
        if self.max_consecutive_losses <= 0:
            raise RiskError("max_consecutive_losses must be positive")
        if self.cooldown_minutes < 0:
            raise RiskError("cooldown_minutes cannot be negative")
        if _d(self.emergency_stop_drawdown_pct) < _d(self.max_drawdown_pct):
            raise RiskError("emergency stop drawdown must be >= max drawdown")


@dataclass(frozen=True)
class RiskInput:
    risk_id: str
    timestamp: str
    symbol: str
    sector: str
    requested_position_fraction: Decimal
    daily_pnl_pct: Decimal
    weekly_pnl_pct: Decimal
    current_drawdown_pct: Decimal
    open_position_count: int
    current_symbol_exposure: Decimal
    current_sector_exposure: Decimal
    portfolio_heat: Decimal
    max_pair_correlation: Decimal
    kelly_fraction: Decimal
    consecutive_losses: int
    decision_hash: str


@dataclass(frozen=True)
class RiskRecord:
    version: str
    risk_id: str
    timestamp: str
    symbol: str
    sector: str
    approved: bool
    emergency_stop: bool
    circuit_breaker: bool
    cooldown_minutes: int
    requested_position_fraction: Decimal
    approved_position_fraction: Decimal
    capped_kelly_fraction: Decimal
    aggregate_risk_score: Decimal
    reason_codes: tuple[str, ...]
    decision_hash: str
    input_hash: str
    risk_hash: str


@dataclass(frozen=True)
class RiskHistory:
    version: str
    records: tuple[RiskRecord, ...]
    history_hash: str


def _validate_sha256(value: str, field_name: str) -> str:
    digest = value.strip().lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise RiskError(f"{field_name} must be a SHA-256 hex digest")
    return digest


def _record_payload(record: RiskRecord, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": record.version,
        "risk_id": record.risk_id,
        "timestamp": record.timestamp,
        "symbol": record.symbol,
        "sector": record.sector,
        "approved": record.approved,
        "emergency_stop": record.emergency_stop,
        "circuit_breaker": record.circuit_breaker,
        "cooldown_minutes": record.cooldown_minutes,
        "requested_position_fraction": str(record.requested_position_fraction),
        "approved_position_fraction": str(record.approved_position_fraction),
        "capped_kelly_fraction": str(record.capped_kelly_fraction),
        "aggregate_risk_score": str(record.aggregate_risk_score),
        "reason_codes": list(record.reason_codes),
        "decision_hash": record.decision_hash,
        "input_hash": record.input_hash,
    }
    if include_hash:
        payload["risk_hash"] = record.risk_hash
    return payload


def _history_payload(history: RiskHistory, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": history.version,
        "records": [_record_payload(record, include_hash=True) for record in history.records],
    }
    if include_hash:
        payload["history_hash"] = history.history_hash
    return payload


def evaluate_risk(
    item: RiskInput,
    policy: RiskPolicy | None = None,
) -> RiskRecord:
    selected = policy or RiskPolicy()

    risk_id = item.risk_id.strip()
    timestamp = item.timestamp.strip()
    symbol = item.symbol.strip().upper()
    sector = item.sector.strip().upper()

    if not risk_id or not timestamp or not symbol or not sector:
        raise RiskError("risk_id, timestamp, symbol, and sector are required")

    requested = _q(item.requested_position_fraction)
    daily = _q(item.daily_pnl_pct)
    weekly = _q(item.weekly_pnl_pct)
    drawdown = _q(item.current_drawdown_pct)
    symbol_exposure = _q(item.current_symbol_exposure)
    sector_exposure = _q(item.current_sector_exposure)
    heat = _q(item.portfolio_heat)
    correlation = _q(item.max_pair_correlation)
    kelly = _q(item.kelly_fraction)

    for name, value in (
        ("requested_position_fraction", requested),
        ("current_symbol_exposure", symbol_exposure),
        ("current_sector_exposure", sector_exposure),
        ("portfolio_heat", heat),
        ("max_pair_correlation", correlation),
        ("kelly_fraction", kelly),
    ):
        if value < ZERO or value > ONE:
            raise RiskError(f"{name} must be between 0 and 1")

    if drawdown < ZERO:
        raise RiskError("current_drawdown_pct cannot be negative")
    if item.open_position_count < 0:
        raise RiskError("open_position_count cannot be negative")
    if item.consecutive_losses < 0:
        raise RiskError("consecutive_losses cannot be negative")

    decision_hash = _validate_sha256(item.decision_hash, "decision_hash")

    reasons = []
    if daily <= -_d(selected.max_daily_loss_pct):
        reasons.append("DAILY_LOSS_LIMIT")
    if weekly <= -_d(selected.max_weekly_loss_pct):
        reasons.append("WEEKLY_LOSS_LIMIT")
    if drawdown >= _d(selected.max_drawdown_pct):
        reasons.append("MAX_DRAWDOWN")
    if item.open_position_count >= selected.max_open_positions:
        reasons.append("MAX_POSITION_COUNT")
    if symbol_exposure + requested > _d(selected.max_symbol_exposure):
        reasons.append("SYMBOL_EXPOSURE_LIMIT")
    if sector_exposure + requested > _d(selected.max_sector_exposure):
        reasons.append("SECTOR_EXPOSURE_LIMIT")
    if heat + requested > _d(selected.max_portfolio_heat):
        reasons.append("PORTFOLIO_HEAT_LIMIT")
    if correlation > _d(selected.max_correlation):
        reasons.append("CORRELATION_LIMIT")
    if item.consecutive_losses >= selected.max_consecutive_losses:
        reasons.append("CIRCUIT_BREAKER")

    emergency_stop = drawdown >= _d(selected.emergency_stop_drawdown_pct)
    if emergency_stop:
        reasons.append("EMERGENCY_STOP")

    circuit_breaker = "CIRCUIT_BREAKER" in reasons
    cooldown_minutes = selected.cooldown_minutes if circuit_breaker else 0
    capped_kelly = _q(min(kelly, _d(selected.max_kelly_fraction)))
    approved = not reasons

    if approved:
        approved_fraction = _q(min(requested, capped_kelly))
    else:
        approved_fraction = ZERO

    components = (
        min(ONE, abs(daily) / _d(selected.max_daily_loss_pct)),
        min(ONE, abs(weekly) / _d(selected.max_weekly_loss_pct)),
        min(ONE, drawdown / _d(selected.max_drawdown_pct)),
        min(ONE, Decimal(item.open_position_count) / Decimal(selected.max_open_positions)),
        min(ONE, (symbol_exposure + requested) / _d(selected.max_symbol_exposure)),
        min(ONE, (sector_exposure + requested) / _d(selected.max_sector_exposure)),
        min(ONE, (heat + requested) / _d(selected.max_portfolio_heat)),
        min(ONE, correlation / _d(selected.max_correlation)),
    )
    aggregate_risk_score = _q(sum(components, ZERO) / Decimal(len(components)))

    input_hash = _hash({
        "risk_id": risk_id,
        "timestamp": timestamp,
        "symbol": symbol,
        "sector": sector,
        "requested_position_fraction": str(requested),
        "daily_pnl_pct": str(daily),
        "weekly_pnl_pct": str(weekly),
        "current_drawdown_pct": str(drawdown),
        "open_position_count": item.open_position_count,
        "current_symbol_exposure": str(symbol_exposure),
        "current_sector_exposure": str(sector_exposure),
        "portfolio_heat": str(heat),
        "max_pair_correlation": str(correlation),
        "kelly_fraction": str(kelly),
        "consecutive_losses": item.consecutive_losses,
        "decision_hash": decision_hash,
        "policy": {key: str(value) for key, value in selected.__dict__.items()},
    })

    record = RiskRecord(
        version=VERSION,
        risk_id=risk_id,
        timestamp=timestamp,
        symbol=symbol,
        sector=sector,
        approved=approved,
        emergency_stop=emergency_stop,
        circuit_breaker=circuit_breaker,
        cooldown_minutes=cooldown_minutes,
        requested_position_fraction=requested,
        approved_position_fraction=approved_fraction,
        capped_kelly_fraction=capped_kelly,
        aggregate_risk_score=aggregate_risk_score,
        reason_codes=tuple(sorted(set(reasons))),
        decision_hash=decision_hash,
        input_hash=input_hash,
        risk_hash="",
    )
    return replace(record, risk_hash=_hash(_record_payload(record)))


def verify_record(record: RiskRecord) -> bool:
    if record.version != VERSION:
        raise RiskError("unsupported risk version")
    _validate_sha256(record.decision_hash, "decision_hash")
    if not record.risk_id or not record.timestamp or not record.symbol or not record.sector:
        raise RiskError("invalid risk identity")
    if record.approved and record.reason_codes:
        raise RiskError("approved risk record cannot contain blocking reasons")
    if not record.approved and record.approved_position_fraction != ZERO:
        raise RiskError("blocked risk record must have zero position size")
    if record.circuit_breaker and record.cooldown_minutes <= 0:
        raise RiskError("circuit breaker requires cooldown")
    if record.emergency_stop and "EMERGENCY_STOP" not in record.reason_codes:
        raise RiskError("emergency stop reason missing")
    if record.aggregate_risk_score < ZERO or record.aggregate_risk_score > ONE:
        raise RiskError("aggregate risk score out of range")

    clean = replace(record, risk_hash="")
    if record.risk_hash != _hash(_record_payload(clean)):
        raise RiskError("risk hash mismatch")
    return True


def create_history(records: Iterable[RiskRecord]) -> RiskHistory:
    items = tuple(records)
    if not items:
        raise RiskError("risk history cannot be empty")
    if len({record.risk_id for record in items}) != len(items):
        raise RiskError("duplicate risk IDs detected")
    for record in items:
        verify_record(record)

    history = RiskHistory(VERSION, items, "")
    return replace(history, history_hash=_hash(_history_payload(history)))


def verify_history(history: RiskHistory) -> bool:
    if history.version != VERSION:
        raise RiskError("unsupported history version")
    if not history.records:
        raise RiskError("risk history cannot be empty")
    if len({record.risk_id for record in history.records}) != len(history.records):
        raise RiskError("duplicate risk IDs detected")
    for record in history.records:
        verify_record(record)

    clean = replace(history, history_hash="")
    if history.history_hash != _hash(_history_payload(clean)):
        raise RiskError("history hash mismatch")
    return True


def save_history(history: RiskHistory, path: str | Path) -> Path:
    verify_history(history)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_history_payload(history, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_history(path: str | Path) -> RiskHistory:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    records = tuple(
        RiskRecord(
            version=item["version"],
            risk_id=item["risk_id"],
            timestamp=item["timestamp"],
            symbol=item["symbol"],
            sector=item["sector"],
            approved=bool(item["approved"]),
            emergency_stop=bool(item["emergency_stop"]),
            circuit_breaker=bool(item["circuit_breaker"]),
            cooldown_minutes=int(item["cooldown_minutes"]),
            requested_position_fraction=_d(item["requested_position_fraction"]),
            approved_position_fraction=_d(item["approved_position_fraction"]),
            capped_kelly_fraction=_d(item["capped_kelly_fraction"]),
            aggregate_risk_score=_d(item["aggregate_risk_score"]),
            reason_codes=tuple(item["reason_codes"]),
            decision_hash=item["decision_hash"],
            input_hash=item["input_hash"],
            risk_hash=item["risk_hash"],
        )
        for item in payload["records"]
    )
    history = RiskHistory(
        version=payload["version"],
        records=records,
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
