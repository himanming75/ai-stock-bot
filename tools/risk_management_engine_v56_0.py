#!/usr/bin/env python3
"""
V56.0 Risk Management Engine Foundation

Deterministic offline risk approval layer.

Capabilities:
- daily loss limit
- max consecutive losses
- max open positions
- symbol risk limit
- portfolio risk limit
- stop loss validation
- take profit validation
- minimum risk/reward ratio
- trading session validation
- cooldown validation
- duplicate order prevention
- kill switch
- SHA-256 audit hashes
- hash-chain ledger
- live mode intentionally blocked
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, getcontext
from pathlib import Path
from typing import Any, Sequence

getcontext().prec = 40

VERSION = "56.0"
MONEY_Q = Decimal("0.01")
RATIO_Q = Decimal("0.000001")
VALID_ACTIONS = {"BUY", "SELL"}
VALID_MODES = {"replay", "paper", "live"}


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def dec(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result


def money(value: Decimal) -> str:
    return format(value.quantize(MONEY_Q, rounding=ROUND_HALF_UP), "f")


def ratio(value: Decimal) -> str:
    return format(value.quantize(RATIO_Q, rounding=ROUND_HALF_UP), "f")


def parse_utc(value: str, field: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc
    if dt.tzinfo is None:
        raise ValueError(f"{field} must include timezone")
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class RiskState:
    equity: str
    daily_realized_pnl: str
    daily_unrealized_pnl: str
    consecutive_losses: int
    open_position_count: int
    portfolio_risk_amount: str
    symbol_risk_amount: str
    last_trade_time_utc: str | None
    open_order_keys: list[str]
    kill_switch_active: bool
    source_sha256: str


@dataclass(frozen=True)
class RiskRequest:
    request_id: str
    symbol: str
    action: str
    quantity: str
    entry_price: str
    stop_price: str
    take_profit_price: str
    estimated_risk_amount: str
    position_sizing_sha256: str
    requested_at_utc: str
    order_key: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class RiskConfig:
    max_daily_loss_percent: str
    max_consecutive_losses: int
    max_open_positions: int
    max_symbol_risk_percent: str
    max_portfolio_risk_percent: str
    minimum_risk_reward_ratio: str
    session_start_hour_utc: int
    session_end_hour_utc: int
    cooldown_minutes: int
    require_stop_loss: bool
    require_take_profit: bool


@dataclass(frozen=True)
class LedgerEntry:
    sequence: int
    event_type: str
    request_id: str
    symbol: str
    status: str
    decision: str
    previous_entry_sha256: str
    payload_sha256: str
    entry_sha256: str


@dataclass(frozen=True)
class RiskResult:
    schema_version: str
    version: str
    status: str
    decision: str
    request_id: str
    symbol: str
    action: str
    quantity: str
    entry_price: str
    stop_price: str
    take_profit_price: str
    risk_amount: str
    reward_amount: str
    risk_reward_ratio: str
    daily_loss_amount: str
    daily_loss_limit_amount: str
    symbol_risk_after_amount: str
    symbol_risk_limit_amount: str
    portfolio_risk_after_amount: str
    portfolio_risk_limit_amount: str
    rejection_reasons: list[str]
    request_sha256: str
    risk_sha256: str
    network_used: bool
    ledger: list[dict[str, Any]]


class RiskManagementEngine:
    def __init__(self, *, mode: str = "paper", enable_live: bool = False) -> None:
        if mode not in VALID_MODES:
            raise ValueError("mode must be replay, paper, or live")
        self.mode = mode
        self.enable_live = enable_live
        self.ledger: list[LedgerEntry] = []

    def _live_gate(self) -> None:
        if self.mode == "live":
            if not self.enable_live:
                raise PermissionError("live mode requires --enable-live")
            raise NotImplementedError("live risk transport is intentionally not implemented in V56.0")

    @staticmethod
    def _validate_state(state: RiskState) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        equity = dec(state.equity, "equity")
        realized = dec(state.daily_realized_pnl, "daily_realized_pnl")
        unrealized = dec(state.daily_unrealized_pnl, "daily_unrealized_pnl")
        portfolio_risk = dec(state.portfolio_risk_amount, "portfolio_risk_amount")
        symbol_risk = dec(state.symbol_risk_amount, "symbol_risk_amount")
        if equity <= 0:
            raise ValueError("equity must be greater than zero")
        if portfolio_risk < 0 or symbol_risk < 0:
            raise ValueError("risk amounts cannot be negative")
        if state.consecutive_losses < 0 or state.open_position_count < 0:
            raise ValueError("counts cannot be negative")
        if len(state.source_sha256) != 64:
            raise ValueError("source_sha256 must be 64 characters")
        return equity, realized, unrealized, portfolio_risk, symbol_risk

    @staticmethod
    def _validate_config(config: RiskConfig) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        daily_pct = dec(config.max_daily_loss_percent, "max_daily_loss_percent")
        symbol_pct = dec(config.max_symbol_risk_percent, "max_symbol_risk_percent")
        portfolio_pct = dec(config.max_portfolio_risk_percent, "max_portfolio_risk_percent")
        min_rr = dec(config.minimum_risk_reward_ratio, "minimum_risk_reward_ratio")
        for field, value in [
            ("max_daily_loss_percent", daily_pct),
            ("max_symbol_risk_percent", symbol_pct),
            ("max_portfolio_risk_percent", portfolio_pct),
        ]:
            if value < 0 or value > 1:
                raise ValueError(f"{field} must be between 0 and 1")
        if min_rr < 0:
            raise ValueError("minimum_risk_reward_ratio cannot be negative")
        if config.max_consecutive_losses < 0 or config.max_open_positions < 0 or config.cooldown_minutes < 0:
            raise ValueError("limits cannot be negative")
        if not 0 <= config.session_start_hour_utc <= 23 or not 0 <= config.session_end_hour_utc <= 23:
            raise ValueError("session hours must be between 0 and 23")
        return daily_pct, symbol_pct, portfolio_pct, min_rr

    @staticmethod
    def _price_geometry(action: str, entry: Decimal, stop: Decimal, target: Decimal) -> tuple[Decimal, Decimal]:
        if action == "BUY":
            risk_per_share = entry - stop
            reward_per_share = target - entry
        else:
            risk_per_share = stop - entry
            reward_per_share = entry - target
        return risk_per_share, reward_per_share

    @staticmethod
    def _session_allowed(hour: int, start: int, end: int) -> bool:
        if start == end:
            return True
        if start < end:
            return start <= hour < end
        return hour >= start or hour < end

    def _append_ledger(self, core: dict[str, Any]) -> None:
        previous = self.ledger[-1].entry_sha256 if self.ledger else "GENESIS"
        payload = {
            "request_id": core["request_id"],
            "symbol": core["symbol"],
            "status": core["status"],
            "decision": core["decision"],
        }
        payload_sha = canonical_hash(payload)
        entry_core = {
            "sequence": len(self.ledger) + 1,
            "event_type": "RISK_EVALUATED",
            **payload,
            "previous_entry_sha256": previous,
            "payload_sha256": payload_sha,
        }
        self.ledger.append(LedgerEntry(**entry_core, entry_sha256=canonical_hash(entry_core)))

    def evaluate(self, state: RiskState, request: RiskRequest, config: RiskConfig) -> RiskResult:
        self._live_gate()
        equity, realized, unrealized, portfolio_risk, symbol_risk = self._validate_state(state)
        daily_pct, symbol_pct, portfolio_pct, min_rr = self._validate_config(config)

        reasons: list[str] = []
        symbol = request.symbol.upper().strip()
        action = request.action.upper().strip()

        if not request.request_id.strip():
            reasons.append("request_id_required")
        if not symbol:
            reasons.append("symbol_required")
        if action not in VALID_ACTIONS:
            reasons.append("invalid_action")
        if len(request.position_sizing_sha256) != 64:
            reasons.append("position_sizing_sha256_invalid")
        if not request.order_key.strip():
            reasons.append("order_key_required")

        quantity = dec(request.quantity, "quantity")
        entry = dec(request.entry_price, "entry_price")
        stop = dec(request.stop_price, "stop_price")
        target = dec(request.take_profit_price, "take_profit_price")
        estimated_risk = dec(request.estimated_risk_amount, "estimated_risk_amount")
        requested_at = parse_utc(request.requested_at_utc, "requested_at_utc")

        if quantity <= 0:
            reasons.append("quantity_must_be_positive")
        if entry <= 0:
            reasons.append("entry_price_must_be_positive")
        if estimated_risk < 0:
            reasons.append("estimated_risk_amount_negative")

        if state.kill_switch_active:
            reasons.append("kill_switch_active")
        if request.order_key in state.open_order_keys:
            reasons.append("duplicate_order")
        if state.consecutive_losses >= config.max_consecutive_losses > 0:
            reasons.append("max_consecutive_losses_reached")
        if state.open_position_count >= config.max_open_positions > 0:
            reasons.append("max_open_positions_reached")
        if not self._session_allowed(
            requested_at.hour,
            config.session_start_hour_utc,
            config.session_end_hour_utc,
        ):
            reasons.append("outside_trading_session")

        if state.last_trade_time_utc and config.cooldown_minutes > 0:
            last_trade = parse_utc(state.last_trade_time_utc, "last_trade_time_utc")
            elapsed_minutes = Decimal(str((requested_at - last_trade).total_seconds())) / Decimal("60")
            if elapsed_minutes < 0:
                reasons.append("requested_time_before_last_trade")
            elif elapsed_minutes < config.cooldown_minutes:
                reasons.append("cooldown_active")

        if config.require_stop_loss and stop <= 0:
            reasons.append("stop_loss_required")
        if config.require_take_profit and target <= 0:
            reasons.append("take_profit_required")

        risk_per_share = Decimal("0")
        reward_per_share = Decimal("0")
        rr = Decimal("0")

        if action in VALID_ACTIONS and entry > 0 and stop > 0 and target > 0:
            risk_per_share, reward_per_share = self._price_geometry(action, entry, stop, target)
            if risk_per_share <= 0:
                reasons.append("invalid_stop_loss_geometry")
            if reward_per_share <= 0:
                reasons.append("invalid_take_profit_geometry")
            if risk_per_share > 0 and reward_per_share > 0:
                rr = reward_per_share / risk_per_share
                if rr < min_rr:
                    reasons.append("risk_reward_ratio_below_minimum")

        calculated_risk = max(Decimal("0"), risk_per_share * quantity)
        effective_risk = max(estimated_risk, calculated_risk)
        reward_amount = max(Decimal("0"), reward_per_share * quantity)

        daily_loss = max(Decimal("0"), -(realized + unrealized))
        daily_limit = equity * daily_pct
        if daily_loss >= daily_limit and daily_limit > 0:
            reasons.append("daily_loss_limit_reached")

        symbol_after = symbol_risk + effective_risk
        symbol_limit = equity * symbol_pct
        if symbol_after > symbol_limit:
            reasons.append("symbol_risk_limit_exceeded")

        portfolio_after = portfolio_risk + effective_risk
        portfolio_limit = equity * portfolio_pct
        if portfolio_after > portfolio_limit:
            reasons.append("portfolio_risk_limit_exceeded")

        status = "PASS" if not reasons else "FAIL"
        decision = "risk_approved" if not reasons else "risk_rejected"

        request_payload = {
            "state": asdict(state),
            "request": asdict(request),
            "config": asdict(config),
        }
        request_sha = canonical_hash(request_payload)

        core = {
            "schema_version": "v56.0.risk_management_engine.1",
            "version": VERSION,
            "status": status,
            "decision": decision,
            "request_id": request.request_id,
            "symbol": symbol,
            "action": action,
            "quantity": ratio(quantity),
            "entry_price": money(entry),
            "stop_price": money(stop),
            "take_profit_price": money(target),
            "risk_amount": money(effective_risk),
            "reward_amount": money(reward_amount),
            "risk_reward_ratio": ratio(rr),
            "daily_loss_amount": money(daily_loss),
            "daily_loss_limit_amount": money(daily_limit),
            "symbol_risk_after_amount": money(symbol_after),
            "symbol_risk_limit_amount": money(symbol_limit),
            "portfolio_risk_after_amount": money(portfolio_after),
            "portfolio_risk_limit_amount": money(portfolio_limit),
            "rejection_reasons": reasons,
            "request_sha256": request_sha,
            "network_used": False,
        }
        risk_sha = canonical_hash(core)
        self._append_ledger({**core, "risk_sha256": risk_sha})

        return RiskResult(
            **core,
            risk_sha256=risk_sha,
            ledger=[asdict(entry) for entry in self.ledger],
        )

    @staticmethod
    def export(path: Path, result: RiskResult) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "v56.0.risk_management_engine_export.1",
            "version": VERSION,
            "result": asdict(result),
            "network_used": False,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_payload(path: Path) -> tuple[RiskState, RiskRequest, RiskConfig]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return (
        RiskState(**payload["state"]),
        RiskRequest(**payload["request"]),
        RiskConfig(**payload["config"]),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V56.0 Risk Management Engine Foundation")
    parser.add_argument("--input", required=True)
    parser.add_argument("--mode", choices=sorted(VALID_MODES), default="paper")
    parser.add_argument("--enable-live", action="store_true")
    parser.add_argument("--output", default="release/v56/audit/risk_management_result_v56_0.json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output)
    try:
        state, request, config = load_payload(Path(args.input))
        engine = RiskManagementEngine(mode=args.mode, enable_live=args.enable_live)
        result = engine.evaluate(state, request, config)
        engine.export(output, result)
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
        return 0 if result.status == "PASS" else 1
    except (TypeError, ValueError, PermissionError, NotImplementedError, json.JSONDecodeError, OSError) as exc:
        error = {
            "schema_version": "v56.0.risk_management_engine_error.1",
            "version": VERSION,
            "status": "FAIL",
            "error": str(exc),
            "network_used": False,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(error, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(error, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
