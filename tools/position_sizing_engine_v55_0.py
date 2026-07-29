#!/usr/bin/env python3
"""
V55.0 Position Sizing Engine Foundation

Deterministic, offline position sizing layer.

Capabilities:
- fixed shares
- fixed dollar
- fixed percent of equity
- fixed risk per trade
- ATR risk sizing
- optional Kelly fraction
- cash and buying power checks
- max position and portfolio exposure limits
- lot size and fractional share controls
- minimum/maximum order limits
- SHA-256 audit hashes
- hash-chain ledger
- live mode intentionally blocked
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_UP, getcontext
from pathlib import Path
from typing import Any, Sequence

getcontext().prec = 40

VERSION = "55.0"
MONEY_Q = Decimal("0.01")
RATIO_Q = Decimal("0.000001")
VALID_METHODS = {
    "fixed_shares",
    "fixed_dollar",
    "fixed_percent_equity",
    "fixed_risk",
    "atr_risk",
    "kelly_fraction",
}
VALID_ACTIONS = {"BUY", "SELL", "HOLD"}
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


@dataclass(frozen=True)
class AccountState:
    equity: str
    cash: str
    buying_power: str
    current_gross_exposure: str
    source_sha256: str


@dataclass(frozen=True)
class PositionSizingRequest:
    request_id: str
    symbol: str
    action: str
    entry_price: str
    method: str
    signal_sha256: str
    fixed_shares: str | None
    fixed_dollar: str | None
    percent_of_equity: str | None
    risk_percent: str | None
    stop_price: str | None
    atr: str | None
    atr_multiple: str | None
    win_rate: str | None
    payoff_ratio: str | None
    kelly_fraction_cap: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class PositionSizingConfig:
    allow_fractional_shares: bool
    lot_size: str
    min_order_notional: str
    max_order_notional: str
    max_position_percent: str
    max_portfolio_exposure_percent: str
    reserve_cash_percent: str


@dataclass(frozen=True)
class PositionSizingResult:
    schema_version: str
    version: str
    status: str
    decision: str
    request_id: str
    symbol: str
    action: str
    sizing_method: str
    shares: str
    entry_price: str
    position_notional: str
    estimated_risk_amount: str
    available_capital: str
    max_position_notional: str
    max_portfolio_additional_notional: str
    limiting_factors: list[str]
    rejection_reasons: list[str]
    request_sha256: str
    sizing_sha256: str
    network_used: bool
    ledger: list[dict[str, Any]]


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


class PositionSizingEngine:
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
            raise NotImplementedError("live position sizing transport is intentionally not implemented in V55.0")

    @staticmethod
    def _validate_account(account: AccountState) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        equity = dec(account.equity, "equity")
        cash = dec(account.cash, "cash")
        buying_power = dec(account.buying_power, "buying_power")
        exposure = dec(account.current_gross_exposure, "current_gross_exposure")
        if equity <= 0:
            raise ValueError("equity must be greater than zero")
        if cash < 0 or buying_power < 0 or exposure < 0:
            raise ValueError("cash, buying_power, and current_gross_exposure cannot be negative")
        if len(account.source_sha256) != 64:
            raise ValueError("account source_sha256 must be 64 characters")
        return equity, cash, buying_power, exposure

    @staticmethod
    def _validate_config(config: PositionSizingConfig) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Decimal]:
        lot = dec(config.lot_size, "lot_size")
        min_notional = dec(config.min_order_notional, "min_order_notional")
        max_notional = dec(config.max_order_notional, "max_order_notional")
        max_position_pct = dec(config.max_position_percent, "max_position_percent")
        max_portfolio_pct = dec(config.max_portfolio_exposure_percent, "max_portfolio_exposure_percent")
        reserve_pct = dec(config.reserve_cash_percent, "reserve_cash_percent")
        if lot <= 0:
            raise ValueError("lot_size must be greater than zero")
        if min_notional < 0 or max_notional <= 0 or min_notional > max_notional:
            raise ValueError("order notional limits are invalid")
        for field, value in [
            ("max_position_percent", max_position_pct),
            ("max_portfolio_exposure_percent", max_portfolio_pct),
            ("reserve_cash_percent", reserve_pct),
        ]:
            if value < 0 or value > 1:
                raise ValueError(f"{field} must be between 0 and 1")
        return lot, min_notional, max_notional, max_position_pct, max_portfolio_pct, reserve_pct

    @staticmethod
    def _floor_shares(shares: Decimal, lot: Decimal, allow_fractional: bool) -> Decimal:
        if shares <= 0:
            return Decimal("0")
        if allow_fractional:
            units = (shares / lot).to_integral_value(rounding=ROUND_DOWN)
            return units * lot
        whole_lot = max(lot, Decimal("1"))
        units = (shares / whole_lot).to_integral_value(rounding=ROUND_DOWN)
        return units * whole_lot

    @staticmethod
    def _kelly_fraction(win_rate: Decimal, payoff_ratio: Decimal) -> Decimal:
        if win_rate < 0 or win_rate > 1:
            raise ValueError("win_rate must be between 0 and 1")
        if payoff_ratio <= 0:
            raise ValueError("payoff_ratio must be greater than zero")
        loss_rate = Decimal("1") - win_rate
        kelly = win_rate - (loss_rate / payoff_ratio)
        return max(Decimal("0"), kelly)

    def _raw_target_notional(
        self,
        request: PositionSizingRequest,
        equity: Decimal,
        entry: Decimal,
    ) -> tuple[Decimal, Decimal]:
        method = request.method
        risk_amount = Decimal("0")

        if method == "fixed_shares":
            shares = dec(request.fixed_shares, "fixed_shares")
            if shares <= 0:
                raise ValueError("fixed_shares must be greater than zero")
            return shares * entry, risk_amount

        if method == "fixed_dollar":
            amount = dec(request.fixed_dollar, "fixed_dollar")
            if amount <= 0:
                raise ValueError("fixed_dollar must be greater than zero")
            return amount, risk_amount

        if method == "fixed_percent_equity":
            pct = dec(request.percent_of_equity, "percent_of_equity")
            if pct <= 0 or pct > 1:
                raise ValueError("percent_of_equity must be between 0 and 1")
            return equity * pct, risk_amount

        if method in {"fixed_risk", "atr_risk"}:
            risk_pct = dec(request.risk_percent, "risk_percent")
            if risk_pct <= 0 or risk_pct > 1:
                raise ValueError("risk_percent must be between 0 and 1")
            risk_amount = equity * risk_pct

            if method == "fixed_risk":
                stop = dec(request.stop_price, "stop_price")
                per_share_risk = abs(entry - stop)
            else:
                atr = dec(request.atr, "atr")
                multiple = dec(request.atr_multiple, "atr_multiple")
                if atr <= 0 or multiple <= 0:
                    raise ValueError("atr and atr_multiple must be greater than zero")
                per_share_risk = atr * multiple

            if per_share_risk <= 0:
                raise ValueError("per-share risk must be greater than zero")
            return (risk_amount / per_share_risk) * entry, risk_amount

        if method == "kelly_fraction":
            win_rate = dec(request.win_rate, "win_rate")
            payoff = dec(request.payoff_ratio, "payoff_ratio")
            cap = dec(request.kelly_fraction_cap, "kelly_fraction_cap")
            if cap <= 0 or cap > 1:
                raise ValueError("kelly_fraction_cap must be between 0 and 1")
            fraction = min(self._kelly_fraction(win_rate, payoff), cap)
            return equity * fraction, risk_amount

        raise ValueError("unsupported sizing method")

    def _append_ledger(self, result_core: dict[str, Any]) -> None:
        previous = self.ledger[-1].entry_sha256 if self.ledger else "GENESIS"
        payload = {
            "request_id": result_core["request_id"],
            "symbol": result_core["symbol"],
            "status": result_core["status"],
            "decision": result_core["decision"],
        }
        payload_sha = canonical_hash(payload)
        core = {
            "sequence": len(self.ledger) + 1,
            "event_type": "POSITION_SIZED",
            **payload,
            "previous_entry_sha256": previous,
            "payload_sha256": payload_sha,
        }
        self.ledger.append(LedgerEntry(**core, entry_sha256=canonical_hash(core)))

    def size(
        self,
        account: AccountState,
        request: PositionSizingRequest,
        config: PositionSizingConfig,
    ) -> PositionSizingResult:
        self._live_gate()

        equity, cash, buying_power, exposure = self._validate_account(account)
        lot, min_notional, max_notional, max_pos_pct, max_port_pct, reserve_pct = self._validate_config(config)

        reasons: list[str] = []
        limiting: list[str] = []

        symbol = request.symbol.upper().strip()
        action = request.action.upper().strip()
        method = request.method.strip()

        if not request.request_id.strip():
            reasons.append("request_id_required")
        if not symbol:
            reasons.append("symbol_required")
        if action not in VALID_ACTIONS:
            reasons.append("invalid_action")
        if method not in VALID_METHODS:
            reasons.append("invalid_sizing_method")
        if len(request.signal_sha256) != 64:
            reasons.append("signal_sha256_invalid")

        entry = dec(request.entry_price, "entry_price")
        if entry <= 0:
            reasons.append("entry_price_must_be_positive")

        reserve_cash = equity * reserve_pct
        available_cash = max(Decimal("0"), cash - reserve_cash)
        available_capital = min(available_cash, buying_power)
        max_position_notional = equity * max_pos_pct
        portfolio_limit = equity * max_port_pct
        max_portfolio_additional = max(Decimal("0"), portfolio_limit - exposure)

        target_notional = Decimal("0")
        estimated_risk = Decimal("0")

        if action == "HOLD":
            reasons.append("hold_signal_not_orderable")

        if not reasons:
            try:
                target_notional, estimated_risk = self._raw_target_notional(request, equity, entry)
            except ValueError as exc:
                reasons.append(str(exc))

        capped = target_notional
        caps = [
            ("max_order_notional", max_notional),
            ("max_position_percent", max_position_notional),
            ("max_portfolio_exposure_percent", max_portfolio_additional),
            ("available_capital", available_capital),
        ]
        for name, cap in caps:
            if capped > cap:
                capped = cap
                limiting.append(name)

        raw_shares = capped / entry if entry > 0 else Decimal("0")
        shares = self._floor_shares(raw_shares, lot, config.allow_fractional_shares)
        notional = shares * entry

        if not reasons:
            if shares <= 0:
                reasons.append("calculated_shares_zero")
            if notional < min_notional:
                reasons.append("below_min_order_notional")
            if notional > available_capital:
                reasons.append("insufficient_available_capital")
            if notional > buying_power:
                reasons.append("insufficient_buying_power")

        status = "PASS" if not reasons else "FAIL"
        decision = "size_approved" if not reasons else "reject"

        request_payload = {
            "account": asdict(account),
            "request": asdict(request),
            "config": asdict(config),
        }
        request_sha = canonical_hash(request_payload)

        core = {
            "schema_version": "v55.0.position_sizing_engine.1",
            "version": VERSION,
            "status": status,
            "decision": decision,
            "request_id": request.request_id,
            "symbol": symbol,
            "action": action,
            "sizing_method": method,
            "shares": ratio(shares),
            "entry_price": money(entry),
            "position_notional": money(notional),
            "estimated_risk_amount": money(estimated_risk),
            "available_capital": money(available_capital),
            "max_position_notional": money(max_position_notional),
            "max_portfolio_additional_notional": money(max_portfolio_additional),
            "limiting_factors": limiting,
            "rejection_reasons": reasons,
            "request_sha256": request_sha,
            "network_used": False,
        }
        sizing_sha = canonical_hash(core)
        ledger_core = {**core, "sizing_sha256": sizing_sha}
        self._append_ledger(ledger_core)

        return PositionSizingResult(
            **core,
            sizing_sha256=sizing_sha,
            ledger=[asdict(entry) for entry in self.ledger],
        )

    @staticmethod
    def export(path: Path, result: PositionSizingResult) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "v55.0.position_sizing_engine_export.1",
            "version": VERSION,
            "result": asdict(result),
            "network_used": False,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_payload(path: Path) -> tuple[AccountState, PositionSizingRequest, PositionSizingConfig]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return (
        AccountState(**payload["account"]),
        PositionSizingRequest(**payload["request"]),
        PositionSizingConfig(**payload["config"]),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V55.0 Position Sizing Engine Foundation")
    parser.add_argument("--input", required=True)
    parser.add_argument("--mode", choices=sorted(VALID_MODES), default="paper")
    parser.add_argument("--enable-live", action="store_true")
    parser.add_argument("--output", default="release/v55/audit/position_sizing_result_v55_0.json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output)
    try:
        account, request, config = load_payload(Path(args.input))
        engine = PositionSizingEngine(mode=args.mode, enable_live=args.enable_live)
        result = engine.size(account, request, config)
        engine.export(output, result)
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
        return 0 if result.status == "PASS" else 1
    except (TypeError, ValueError, PermissionError, NotImplementedError, json.JSONDecodeError, OSError) as exc:
        error = {
            "schema_version": "v55.0.position_sizing_engine_error.1",
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
