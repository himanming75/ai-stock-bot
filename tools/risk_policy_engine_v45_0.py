#!/usr/bin/env python3
"""
V45.0 Risk Policy Engine Foundation

Consumes a V44 order validation result and applies account-level trading policy.

Checks:
- V44 validation status and integrity
- live safety gate
- per-order risk amount and risk percentage
- max position weight after order
- max symbol exposure after order
- max gross exposure after order
- max open positions
- duplicate symbol entry
- daily realized loss limit
- consecutive loss limit
- daily trade count limit
- cooldown after loss
- portfolio drawdown limit
- cash reserve floor
- order-side consistency

No broker, network, or live order submission is implemented.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Sequence


VERSION = "45.0"


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def to_decimal(value: Any, name: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not number.is_finite():
        raise ValueError(f"{name} must be finite")
    return number


def nonnegative(value: Any, name: str) -> Decimal:
    number = to_decimal(value, name)
    if number < 0:
        raise ValueError(f"{name} must be zero or greater")
    return number


def positive(value: Any, name: str) -> Decimal:
    number = to_decimal(value, name)
    if number <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return number


def normalize(number: Decimal) -> str:
    if number == 0:
        return "0"
    return format(number.normalize(), "f")


@dataclass(frozen=True)
class RiskPolicyConfig:
    max_order_risk_amount: str = "1000"
    max_order_risk_pct: str = "1"
    max_position_weight_pct: str = "20"
    max_symbol_exposure_pct: str = "25"
    max_gross_exposure_pct: str = "100"
    max_open_positions: int = 10
    max_daily_realized_loss: str = "2000"
    max_consecutive_losses: int = 3
    max_daily_trades: int = 20
    cooldown_seconds_after_loss: int = 900
    max_portfolio_drawdown_pct: str = "10"
    minimum_cash_reserve_pct: str = "10"
    allow_duplicate_symbol_entry: bool = False

    def validate(self) -> None:
        positive(self.max_order_risk_amount, "max_order_risk_amount")
        positive(self.max_order_risk_pct, "max_order_risk_pct")
        positive(self.max_position_weight_pct, "max_position_weight_pct")
        positive(self.max_symbol_exposure_pct, "max_symbol_exposure_pct")
        positive(self.max_gross_exposure_pct, "max_gross_exposure_pct")
        positive(self.max_daily_realized_loss, "max_daily_realized_loss")
        positive(self.max_portfolio_drawdown_pct, "max_portfolio_drawdown_pct")
        nonnegative(self.minimum_cash_reserve_pct, "minimum_cash_reserve_pct")
        if self.max_open_positions < 1:
            raise ValueError("max_open_positions must be at least 1")
        if self.max_consecutive_losses < 1:
            raise ValueError("max_consecutive_losses must be at least 1")
        if self.max_daily_trades < 1:
            raise ValueError("max_daily_trades must be at least 1")
        if self.cooldown_seconds_after_loss < 0:
            raise ValueError("cooldown_seconds_after_loss must be zero or greater")


@dataclass(frozen=True)
class OrderValidationInput:
    schema_version: str
    version: str
    status: str
    symbol: str
    client_order_id: str | None
    side: str | None
    quantity: str
    reference_price: str | None
    order_notional: str | None
    checks: list[dict[str, Any]]
    rejection_reasons: list[str]
    network_used: bool
    validation_sha256: str


@dataclass(frozen=True)
class AccountRiskState:
    equity: str
    cash: str
    gross_exposure: str
    symbol_exposure: str
    open_positions: int
    symbol_already_open: bool
    daily_realized_pnl: str
    consecutive_losses: int
    daily_trade_count: int
    last_loss_at: str | None
    peak_equity: str
    current_equity: str


@dataclass(frozen=True)
class RiskPolicyDecision:
    schema_version: str
    version: str
    status: str
    decision: str
    symbol: str
    client_order_id: str | None
    side: str | None
    order_notional: str | None
    estimated_risk_amount: str
    estimated_risk_pct: str
    projected_position_weight_pct: str
    projected_symbol_exposure_pct: str
    projected_gross_exposure_pct: str
    projected_cash_reserve_pct: str
    checks: list[dict[str, Any]]
    rejection_reasons: list[str]
    network_used: bool
    decision_sha256: str


class RiskPolicyEngine:
    def __init__(
        self,
        config: RiskPolicyConfig | None = None,
        *,
        mode: str = "paper",
        enable_live: bool = False,
        reference_time: str | None = None,
    ) -> None:
        self.config = config or RiskPolicyConfig()
        self.config.validate()
        if mode not in {"replay", "paper", "live"}:
            raise ValueError("mode must be replay, paper, or live")
        self.mode = mode
        self.enable_live = enable_live
        self.reference_time = (
            parse_timestamp(reference_time)
            if reference_time
            else datetime.now(timezone.utc)
        )

    def _live_gate(self) -> None:
        if self.mode == "live":
            if not self.enable_live:
                raise PermissionError("live mode requires --enable-live")
            raise NotImplementedError(
                "live broker execution is intentionally not implemented in V45.0"
            )

    @staticmethod
    def _validation_hash_payload(validation: OrderValidationInput) -> dict[str, Any]:
        return {
            "schema_version": validation.schema_version,
            "version": validation.version,
            "status": validation.status,
            "symbol": validation.symbol,
            "client_order_id": validation.client_order_id,
            "side": validation.side,
            "quantity": validation.quantity,
            "reference_price": validation.reference_price,
            "order_notional": validation.order_notional,
            "checks": validation.checks,
            "rejection_reasons": validation.rejection_reasons,
            "network_used": validation.network_used,
        }

    def evaluate(
        self,
        validation: OrderValidationInput,
        account: AccountRiskState,
        *,
        stop_price: Any,
    ) -> RiskPolicyDecision:
        self._live_gate()

        checks: list[dict[str, Any]] = []
        reasons: list[str] = []

        def record(check_id: str, passed: bool, message: str) -> None:
            checks.append(
                {
                    "check_id": check_id,
                    "status": "PASS" if passed else "FAIL",
                    "message": message,
                }
            )
            if not passed:
                reasons.append(message)

        expected_validation_hash = canonical_hash(
            self._validation_hash_payload(validation)
        )
        record(
            "validation.status",
            validation.status == "PASS",
            "V44 order validation status must be PASS.",
        )
        record(
            "validation.hash",
            expected_validation_hash == validation.validation_sha256,
            "V44 validation SHA-256 verification failed.",
        )
        record(
            "validation.network",
            validation.network_used is False,
            "V44 validation must report network_used=false.",
        )

        symbol = validation.symbol.strip().upper()
        side = validation.side.lower() if validation.side else None
        record("order.side", side in {"buy", "sell"}, "Order side must be buy or sell.")

        equity = positive(account.equity, "equity")
        cash = nonnegative(account.cash, "cash")
        gross_exposure = nonnegative(account.gross_exposure, "gross_exposure")
        symbol_exposure = nonnegative(account.symbol_exposure, "symbol_exposure")
        peak_equity = positive(account.peak_equity, "peak_equity")
        current_equity = positive(account.current_equity, "current_equity")
        daily_realized_pnl = to_decimal(
            account.daily_realized_pnl, "daily_realized_pnl"
        )

        if validation.order_notional is None:
            order_notional = Decimal("0")
            record("order.notional", False, "Order notional is required.")
        else:
            try:
                order_notional = positive(
                    validation.order_notional, "order_notional"
                )
                record("order.notional", True, "Order notional is valid.")
            except ValueError as exc:
                order_notional = Decimal("0")
                record("order.notional", False, str(exc))

        if validation.reference_price is None:
            reference_price = Decimal("0")
            record("order.reference_price", False, "Reference price is required.")
        else:
            try:
                reference_price = positive(
                    validation.reference_price, "reference_price"
                )
                record(
                    "order.reference_price",
                    True,
                    "Reference price is valid.",
                )
            except ValueError as exc:
                reference_price = Decimal("0")
                record("order.reference_price", False, str(exc))

        quantity = positive(validation.quantity, "quantity")
        stop = positive(stop_price, "stop_price")

        estimated_risk_amount = abs(reference_price - stop) * quantity
        estimated_risk_pct = (
            estimated_risk_amount / equity * Decimal("100")
            if equity > 0
            else Decimal("0")
        )

        max_risk_amount = to_decimal(
            self.config.max_order_risk_amount, "max_order_risk_amount"
        )
        max_risk_pct = to_decimal(
            self.config.max_order_risk_pct, "max_order_risk_pct"
        )
        record(
            "risk.amount",
            estimated_risk_amount <= max_risk_amount,
            f"Estimated order risk exceeds {normalize(max_risk_amount)}.",
        )
        record(
            "risk.percent",
            estimated_risk_pct <= max_risk_pct,
            f"Estimated order risk percent exceeds {normalize(max_risk_pct)}%.",
        )

        if side == "buy":
            projected_symbol_exposure = symbol_exposure + order_notional
            projected_gross_exposure = gross_exposure + order_notional
            projected_cash = cash - order_notional
            projected_position_count = (
                account.open_positions
                if account.symbol_already_open
                else account.open_positions + 1
            )
        elif side == "sell":
            projected_symbol_exposure = max(
                Decimal("0"), symbol_exposure - order_notional
            )
            projected_gross_exposure = max(
                Decimal("0"), gross_exposure - order_notional
            )
            projected_cash = cash + order_notional
            projected_position_count = account.open_positions
        else:
            projected_symbol_exposure = symbol_exposure
            projected_gross_exposure = gross_exposure
            projected_cash = cash
            projected_position_count = account.open_positions

        projected_symbol_exposure_pct = (
            projected_symbol_exposure / equity * Decimal("100")
        )
        projected_gross_exposure_pct = (
            projected_gross_exposure / equity * Decimal("100")
        )
        projected_position_weight_pct = projected_symbol_exposure_pct
        projected_cash_reserve_pct = projected_cash / equity * Decimal("100")

        max_position_weight_pct = to_decimal(
            self.config.max_position_weight_pct, "max_position_weight_pct"
        )
        max_symbol_exposure_pct = to_decimal(
            self.config.max_symbol_exposure_pct, "max_symbol_exposure_pct"
        )
        max_gross_exposure_pct = to_decimal(
            self.config.max_gross_exposure_pct, "max_gross_exposure_pct"
        )
        minimum_cash_reserve_pct = to_decimal(
            self.config.minimum_cash_reserve_pct, "minimum_cash_reserve_pct"
        )

        record(
            "position.weight",
            projected_position_weight_pct <= max_position_weight_pct,
            f"Projected position weight exceeds {normalize(max_position_weight_pct)}%.",
        )
        record(
            "exposure.symbol",
            projected_symbol_exposure_pct <= max_symbol_exposure_pct,
            f"Projected symbol exposure exceeds {normalize(max_symbol_exposure_pct)}%.",
        )
        record(
            "exposure.gross",
            projected_gross_exposure_pct <= max_gross_exposure_pct,
            f"Projected gross exposure exceeds {normalize(max_gross_exposure_pct)}%.",
        )
        record(
            "positions.count",
            projected_position_count <= self.config.max_open_positions,
            f"Projected open position count exceeds {self.config.max_open_positions}.",
        )

        duplicate_entry_blocked = (
            side == "buy"
            and account.symbol_already_open
            and not self.config.allow_duplicate_symbol_entry
        )
        record(
            "symbol.duplicate_entry",
            not duplicate_entry_blocked,
            "Duplicate symbol entry is not allowed.",
        )

        daily_loss = abs(min(daily_realized_pnl, Decimal("0")))
        max_daily_loss = to_decimal(
            self.config.max_daily_realized_loss, "max_daily_realized_loss"
        )
        record(
            "loss.daily",
            daily_loss < max_daily_loss,
            f"Daily realized loss reached the limit {normalize(max_daily_loss)}.",
        )
        record(
            "loss.consecutive",
            account.consecutive_losses < self.config.max_consecutive_losses,
            f"Consecutive loss count reached {self.config.max_consecutive_losses}.",
        )
        record(
            "trades.daily_count",
            account.daily_trade_count < self.config.max_daily_trades,
            f"Daily trade count reached {self.config.max_daily_trades}.",
        )

        cooldown_ok = True
        if account.last_loss_at:
            last_loss = parse_timestamp(account.last_loss_at)
            elapsed = (self.reference_time - last_loss).total_seconds()
            cooldown_ok = elapsed >= self.config.cooldown_seconds_after_loss
        record(
            "loss.cooldown",
            cooldown_ok,
            f"Loss cooldown of {self.config.cooldown_seconds_after_loss} seconds is active.",
        )

        drawdown_pct = max(
            Decimal("0"),
            (peak_equity - current_equity) / peak_equity * Decimal("100"),
        )
        max_drawdown_pct = to_decimal(
            self.config.max_portfolio_drawdown_pct,
            "max_portfolio_drawdown_pct",
        )
        record(
            "portfolio.drawdown",
            drawdown_pct <= max_drawdown_pct,
            f"Portfolio drawdown exceeds {normalize(max_drawdown_pct)}%.",
        )
        record(
            "cash.reserve",
            projected_cash_reserve_pct >= minimum_cash_reserve_pct,
            f"Projected cash reserve falls below {normalize(minimum_cash_reserve_pct)}%.",
        )

        status = "PASS" if not reasons else "FAIL"
        decision = "approve" if status == "PASS" else "reject"

        core = {
            "schema_version": "v45.0.risk_policy_decision.1",
            "version": VERSION,
            "status": status,
            "decision": decision,
            "symbol": symbol,
            "client_order_id": validation.client_order_id,
            "side": side,
            "order_notional": (
                normalize(order_notional) if order_notional > 0 else None
            ),
            "estimated_risk_amount": normalize(estimated_risk_amount),
            "estimated_risk_pct": normalize(estimated_risk_pct),
            "projected_position_weight_pct": normalize(
                projected_position_weight_pct
            ),
            "projected_symbol_exposure_pct": normalize(
                projected_symbol_exposure_pct
            ),
            "projected_gross_exposure_pct": normalize(
                projected_gross_exposure_pct
            ),
            "projected_cash_reserve_pct": normalize(
                projected_cash_reserve_pct
            ),
            "checks": checks,
            "rejection_reasons": reasons,
            "network_used": False,
        }
        return RiskPolicyDecision(
            **core,
            decision_sha256=canonical_hash(core),
        )

    @staticmethod
    def export(path: Path, decision: RiskPolicyDecision) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "v45.0.risk_policy_export.1",
            "version": VERSION,
            "decision": asdict(decision),
            "network_used": False,
        }
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def load_validation(path: Path) -> OrderValidationInput:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("result", payload)
    return OrderValidationInput(**raw)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="V45.0 Risk Policy Engine Foundation"
    )
    parser.add_argument(
        "--input",
        default="release/v44/audit/order_validation_result_v44_0.json",
    )
    parser.add_argument("--stop-price", required=True)
    parser.add_argument("--equity", default="100000")
    parser.add_argument("--cash", default="50000")
    parser.add_argument("--gross-exposure", default="30000")
    parser.add_argument("--symbol-exposure", default="10000")
    parser.add_argument("--open-positions", type=int, default=3)
    parser.add_argument("--symbol-already-open", action="store_true")
    parser.add_argument("--daily-realized-pnl", default="0")
    parser.add_argument("--consecutive-losses", type=int, default=0)
    parser.add_argument("--daily-trade-count", type=int, default=0)
    parser.add_argument("--last-loss-at")
    parser.add_argument("--peak-equity", default="100000")
    parser.add_argument("--current-equity", default="100000")

    parser.add_argument("--max-order-risk-amount", default="1000")
    parser.add_argument("--max-order-risk-pct", default="1")
    parser.add_argument("--max-position-weight-pct", default="20")
    parser.add_argument("--max-symbol-exposure-pct", default="25")
    parser.add_argument("--max-gross-exposure-pct", default="100")
    parser.add_argument("--max-open-positions", type=int, default=10)
    parser.add_argument("--max-daily-realized-loss", default="2000")
    parser.add_argument("--max-consecutive-losses", type=int, default=3)
    parser.add_argument("--max-daily-trades", type=int, default=20)
    parser.add_argument("--cooldown-seconds-after-loss", type=int, default=900)
    parser.add_argument("--max-portfolio-drawdown-pct", default="10")
    parser.add_argument("--minimum-cash-reserve-pct", default="10")
    parser.add_argument("--allow-duplicate-symbol-entry", action="store_true")

    parser.add_argument("--mode", choices=["replay", "paper", "live"], default="paper")
    parser.add_argument("--enable-live", action="store_true")
    parser.add_argument("--reference-time")
    parser.add_argument(
        "--output",
        default="release/v45/audit/risk_policy_result_v45_0.json",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        engine = RiskPolicyEngine(
            RiskPolicyConfig(
                max_order_risk_amount=args.max_order_risk_amount,
                max_order_risk_pct=args.max_order_risk_pct,
                max_position_weight_pct=args.max_position_weight_pct,
                max_symbol_exposure_pct=args.max_symbol_exposure_pct,
                max_gross_exposure_pct=args.max_gross_exposure_pct,
                max_open_positions=args.max_open_positions,
                max_daily_realized_loss=args.max_daily_realized_loss,
                max_consecutive_losses=args.max_consecutive_losses,
                max_daily_trades=args.max_daily_trades,
                cooldown_seconds_after_loss=args.cooldown_seconds_after_loss,
                max_portfolio_drawdown_pct=args.max_portfolio_drawdown_pct,
                minimum_cash_reserve_pct=args.minimum_cash_reserve_pct,
                allow_duplicate_symbol_entry=args.allow_duplicate_symbol_entry,
            ),
            mode=args.mode,
            enable_live=args.enable_live,
            reference_time=args.reference_time,
        )
        validation = load_validation(Path(args.input))
        account = AccountRiskState(
            equity=args.equity,
            cash=args.cash,
            gross_exposure=args.gross_exposure,
            symbol_exposure=args.symbol_exposure,
            open_positions=args.open_positions,
            symbol_already_open=args.symbol_already_open,
            daily_realized_pnl=args.daily_realized_pnl,
            consecutive_losses=args.consecutive_losses,
            daily_trade_count=args.daily_trade_count,
            last_loss_at=args.last_loss_at,
            peak_equity=args.peak_equity,
            current_equity=args.current_equity,
        )
        decision = engine.evaluate(
            validation,
            account,
            stop_price=args.stop_price,
        )
        engine.export(Path(args.output), decision)
        print(json.dumps(asdict(decision), indent=2, sort_keys=True))
        return 0 if decision.status == "PASS" else 1
    except (TypeError, ValueError, PermissionError, NotImplementedError) as exc:
        error = {
            "schema_version": "v45.0.risk_policy_error.1",
            "version": VERSION,
            "status": "FAIL",
            "error": str(exc),
            "network_used": False,
        }
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(error, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(json.dumps(error, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
