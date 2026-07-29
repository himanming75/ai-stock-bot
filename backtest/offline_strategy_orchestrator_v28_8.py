from __future__ import annotations

"""
V28.8 Offline Strategy Orchestrator

Purpose:
Combine offline decision, risk, and portfolio-allocation outputs into a
single deterministic strategy execution plan.

Features:
- decision/risk/allocation binding
- BUY/HOLD/SELL action planning
- blocked-risk HOLD override
- allocation weight reconciliation
- symbol and sector validation
- strategy priority ranking
- cash reserve preservation
- deterministic plan generation
- SHA-256 integrity verification
- strategy history
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

VERSION = "28.8"
ZERO = Decimal("0")
ONE = Decimal("1")
SIX = Decimal("0.000001")


class StrategyError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise StrategyError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise StrategyError("decimal value must be finite")
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
        raise StrategyError(f"{field_name} must be a SHA-256 hex digest")
    return digest


@dataclass(frozen=True)
class StrategyInput:
    strategy_id: str
    timestamp: str
    symbol: str
    sector: str
    decision_label: int
    decision_confidence: Decimal
    decision_position_fraction: Decimal
    risk_approved: bool
    risk_position_fraction: Decimal
    allocation_fraction: Decimal
    expected_return_pct: Decimal
    risk_score: Decimal
    decision_hash: str
    risk_hash: str
    allocation_hash: str


@dataclass(frozen=True)
class StrategyPolicy:
    hold_label: int = 0
    buy_label: int = 1
    sell_label: int = -1
    min_trade_fraction: Decimal = Decimal("0.005")
    max_trade_fraction: Decimal = Decimal("0.15")
    min_confidence: Decimal = Decimal("0.55")
    max_risk_score: Decimal = Decimal("0.65")
    force_hold_on_mismatch: bool = True

    def __post_init__(self) -> None:
        for name in (
            "min_trade_fraction",
            "max_trade_fraction",
            "min_confidence",
            "max_risk_score",
        ):
            value = _d(getattr(self, name))
            if value < ZERO or value > ONE:
                raise StrategyError(f"{name} must be between 0 and 1")
        if self.min_trade_fraction > self.max_trade_fraction:
            raise StrategyError("min_trade_fraction cannot exceed max_trade_fraction")
        if len({self.hold_label, self.buy_label, self.sell_label}) != 3:
            raise StrategyError("strategy labels must be unique")


@dataclass(frozen=True)
class StrategyLine:
    strategy_id: str
    symbol: str
    sector: str
    raw_label: int
    final_action: str
    target_fraction: Decimal
    priority_score: Decimal
    blocked: bool
    reason_codes: tuple[str, ...]
    input_hash: str
    line_hash: str


@dataclass(frozen=True)
class StrategyPlan:
    version: str
    plan_id: str
    lines: tuple[StrategyLine, ...]
    invested_fraction: Decimal
    cash_fraction: Decimal
    executable_count: int
    blocked_count: int
    plan_hash: str


@dataclass(frozen=True)
class StrategyHistory:
    version: str
    plans: tuple[StrategyPlan, ...]
    history_hash: str


def _line_payload(line: StrategyLine, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "strategy_id": line.strategy_id,
        "symbol": line.symbol,
        "sector": line.sector,
        "raw_label": line.raw_label,
        "final_action": line.final_action,
        "target_fraction": str(line.target_fraction),
        "priority_score": str(line.priority_score),
        "blocked": line.blocked,
        "reason_codes": list(line.reason_codes),
        "input_hash": line.input_hash,
    }
    if include_hash:
        payload["line_hash"] = line.line_hash
    return payload


def _plan_payload(plan: StrategyPlan, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": plan.version,
        "plan_id": plan.plan_id,
        "lines": [_line_payload(line, include_hash=True) for line in plan.lines],
        "invested_fraction": str(plan.invested_fraction),
        "cash_fraction": str(plan.cash_fraction),
        "executable_count": plan.executable_count,
        "blocked_count": plan.blocked_count,
    }
    if include_hash:
        payload["plan_hash"] = plan.plan_hash
    return payload


def _history_payload(history: StrategyHistory, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": history.version,
        "plans": [_plan_payload(plan, include_hash=True) for plan in history.plans],
    }
    if include_hash:
        payload["history_hash"] = history.history_hash
    return payload


def _action_for(label: int, policy: StrategyPolicy) -> str:
    if label == policy.buy_label:
        return "BUY"
    if label == policy.sell_label:
        return "SELL"
    if label == policy.hold_label:
        return "HOLD"
    raise StrategyError("unknown decision label")


def _make_line(item: StrategyInput, policy: StrategyPolicy) -> StrategyLine:
    strategy_id = item.strategy_id.strip()
    timestamp = item.timestamp.strip()
    symbol = item.symbol.strip().upper()
    sector = item.sector.strip().upper()

    if not strategy_id or not timestamp or not symbol or not sector:
        raise StrategyError("strategy_id, timestamp, symbol, and sector are required")

    confidence = _q(item.decision_confidence)
    decision_fraction = _q(item.decision_position_fraction)
    risk_fraction = _q(item.risk_position_fraction)
    allocation_fraction = _q(item.allocation_fraction)
    expected_return = _q(item.expected_return_pct)
    risk_score = _q(item.risk_score)

    for name, value in (
        ("decision_confidence", confidence),
        ("decision_position_fraction", decision_fraction),
        ("risk_position_fraction", risk_fraction),
        ("allocation_fraction", allocation_fraction),
        ("risk_score", risk_score),
    ):
        if value < ZERO or value > ONE:
            raise StrategyError(f"{name} must be between 0 and 1")

    decision_hash = _validate_sha256(item.decision_hash, "decision_hash")
    risk_hash = _validate_sha256(item.risk_hash, "risk_hash")
    allocation_hash = _validate_sha256(item.allocation_hash, "allocation_hash")

    raw_action = _action_for(item.decision_label, policy)
    reasons = []

    if confidence < _d(policy.min_confidence):
        reasons.append("LOW_CONFIDENCE")
    if risk_score > _d(policy.max_risk_score):
        reasons.append("RISK_SCORE_EXCEEDED")
    if not item.risk_approved:
        reasons.append("RISK_NOT_APPROVED")

    if item.decision_label != policy.hold_label:
        if decision_fraction <= ZERO:
            reasons.append("ZERO_DECISION_SIZE")
        if risk_fraction <= ZERO:
            reasons.append("ZERO_RISK_SIZE")
        if allocation_fraction <= ZERO:
            reasons.append("ZERO_ALLOCATION")
        if expected_return <= ZERO:
            reasons.append("NON_POSITIVE_EXPECTED_RETURN")

    candidate_fraction = min(
        decision_fraction,
        risk_fraction,
        allocation_fraction,
        _d(policy.max_trade_fraction),
    )

    if item.decision_label == policy.hold_label:
        final_action = "HOLD"
        target_fraction = ZERO
        blocked = False
    elif reasons and policy.force_hold_on_mismatch:
        final_action = "HOLD"
        target_fraction = ZERO
        blocked = True
    elif candidate_fraction < _d(policy.min_trade_fraction):
        final_action = "HOLD"
        target_fraction = ZERO
        blocked = True
        reasons.append("BELOW_MIN_TRADE_SIZE")
    else:
        final_action = raw_action
        target_fraction = _q(candidate_fraction)
        blocked = False

    priority_score = _q(
        confidence * Decimal("0.45")
        + (ONE - risk_score) * Decimal("0.25")
        + min(ONE, max(ZERO, expected_return / Decimal("10"))) * Decimal("0.20")
        + min(ONE, allocation_fraction / max(_d(policy.max_trade_fraction), SIX)) * Decimal("0.10")
    )

    input_hash = _hash({
        "strategy_id": strategy_id,
        "timestamp": timestamp,
        "symbol": symbol,
        "sector": sector,
        "decision_label": item.decision_label,
        "decision_confidence": str(confidence),
        "decision_position_fraction": str(decision_fraction),
        "risk_approved": item.risk_approved,
        "risk_position_fraction": str(risk_fraction),
        "allocation_fraction": str(allocation_fraction),
        "expected_return_pct": str(expected_return),
        "risk_score": str(risk_score),
        "decision_hash": decision_hash,
        "risk_hash": risk_hash,
        "allocation_hash": allocation_hash,
        "policy": {key: str(value) for key, value in policy.__dict__.items()},
    })

    line = StrategyLine(
        strategy_id=strategy_id,
        symbol=symbol,
        sector=sector,
        raw_label=item.decision_label,
        final_action=final_action,
        target_fraction=target_fraction,
        priority_score=priority_score,
        blocked=blocked,
        reason_codes=tuple(sorted(set(reasons))),
        input_hash=input_hash,
        line_hash="",
    )
    return replace(line, line_hash=_hash(_line_payload(line)))


def create_strategy_plan(
    items: Iterable[StrategyInput],
    policy: StrategyPolicy | None = None,
) -> StrategyPlan:
    selected = policy or StrategyPolicy()
    values = tuple(items)
    if not values:
        raise StrategyError("at least one strategy input is required")
    if len({item.strategy_id for item in values}) != len(values):
        raise StrategyError("duplicate strategy IDs detected")
    if len({item.symbol.strip().upper() for item in values}) != len(values):
        raise StrategyError("duplicate symbols detected")

    lines = tuple(_make_line(item, selected) for item in values)
    ranked = tuple(sorted(
        lines,
        key=lambda line: (line.priority_score, line.symbol),
        reverse=True,
    ))

    invested = _q(sum(
        (line.target_fraction for line in ranked if line.final_action != "HOLD"),
        ZERO,
    ))
    if invested > ONE:
        raise StrategyError("strategy plan exceeds total portfolio fraction")
    cash = _q(ONE - invested)

    input_hash = _hash({
        "line_hashes": [line.line_hash for line in ranked],
        "version": VERSION,
    })

    plan = StrategyPlan(
        version=VERSION,
        plan_id=f"PLAN-{input_hash[:16].upper()}",
        lines=ranked,
        invested_fraction=invested,
        cash_fraction=cash,
        executable_count=sum(line.final_action != "HOLD" for line in ranked),
        blocked_count=sum(line.blocked for line in ranked),
        plan_hash="",
    )
    return replace(plan, plan_hash=_hash(_plan_payload(plan)))


def verify_line(line: StrategyLine) -> bool:
    if not line.strategy_id or not line.symbol or not line.sector:
        raise StrategyError("invalid strategy line identity")
    if line.final_action not in {"BUY", "SELL", "HOLD"}:
        raise StrategyError("invalid final action")
    if line.target_fraction < ZERO or line.target_fraction > ONE:
        raise StrategyError("target fraction out of range")
    if line.final_action == "HOLD" and line.target_fraction != ZERO:
        raise StrategyError("HOLD line must have zero target fraction")
    if line.blocked and not line.reason_codes:
        raise StrategyError("blocked line requires reason codes")
    clean = replace(line, line_hash="")
    if line.line_hash != _hash(_line_payload(clean)):
        raise StrategyError("strategy line hash mismatch")
    return True


def verify_plan(plan: StrategyPlan) -> bool:
    if plan.version != VERSION:
        raise StrategyError("unsupported plan version")
    if not plan.plan_id.startswith("PLAN-"):
        raise StrategyError("invalid plan ID")
    if not plan.lines:
        raise StrategyError("strategy plan cannot be empty")
    if len({line.strategy_id for line in plan.lines}) != len(plan.lines):
        raise StrategyError("duplicate strategy IDs detected")
    if len({line.symbol for line in plan.lines}) != len(plan.lines):
        raise StrategyError("duplicate symbols detected")
    for line in plan.lines:
        verify_line(line)

    invested = sum(
        (line.target_fraction for line in plan.lines if line.final_action != "HOLD"),
        ZERO,
    )
    if invested != plan.invested_fraction:
        raise StrategyError("invested fraction mismatch")
    if plan.invested_fraction + plan.cash_fraction != Decimal("1.000000"):
        raise StrategyError("plan fractions must sum to one")
    if plan.executable_count != sum(line.final_action != "HOLD" for line in plan.lines):
        raise StrategyError("executable count mismatch")
    if plan.blocked_count != sum(line.blocked for line in plan.lines):
        raise StrategyError("blocked count mismatch")

    clean = replace(plan, plan_hash="")
    if plan.plan_hash != _hash(_plan_payload(clean)):
        raise StrategyError("strategy plan hash mismatch")
    return True


def create_history(plans: Iterable[StrategyPlan]) -> StrategyHistory:
    items = tuple(plans)
    if not items:
        raise StrategyError("strategy history cannot be empty")
    if len({plan.plan_id for plan in items}) != len(items):
        raise StrategyError("duplicate plan IDs detected")
    for plan in items:
        verify_plan(plan)
    history = StrategyHistory(VERSION, items, "")
    return replace(history, history_hash=_hash(_history_payload(history)))


def verify_history(history: StrategyHistory) -> bool:
    if history.version != VERSION:
        raise StrategyError("unsupported history version")
    if not history.plans:
        raise StrategyError("strategy history cannot be empty")
    if len({plan.plan_id for plan in history.plans}) != len(history.plans):
        raise StrategyError("duplicate plan IDs detected")
    for plan in history.plans:
        verify_plan(plan)
    clean = replace(history, history_hash="")
    if history.history_hash != _hash(_history_payload(clean)):
        raise StrategyError("history hash mismatch")
    return True


def save_history(history: StrategyHistory, path: str | Path) -> Path:
    verify_history(history)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_history_payload(history, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_history(path: str | Path) -> StrategyHistory:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    plans = []
    for plan_data in payload["plans"]:
        lines = tuple(
            StrategyLine(
                strategy_id=item["strategy_id"],
                symbol=item["symbol"],
                sector=item["sector"],
                raw_label=int(item["raw_label"]),
                final_action=item["final_action"],
                target_fraction=_d(item["target_fraction"]),
                priority_score=_d(item["priority_score"]),
                blocked=bool(item["blocked"]),
                reason_codes=tuple(item["reason_codes"]),
                input_hash=item["input_hash"],
                line_hash=item["line_hash"],
            )
            for item in plan_data["lines"]
        )
        plans.append(StrategyPlan(
            version=plan_data["version"],
            plan_id=plan_data["plan_id"],
            lines=lines,
            invested_fraction=_d(plan_data["invested_fraction"]),
            cash_fraction=_d(plan_data["cash_fraction"]),
            executable_count=int(plan_data["executable_count"]),
            blocked_count=int(plan_data["blocked_count"]),
            plan_hash=plan_data["plan_hash"],
        ))
    history = StrategyHistory(
        version=payload["version"],
        plans=tuple(plans),
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
