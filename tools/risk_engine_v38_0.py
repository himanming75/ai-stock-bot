#!/usr/bin/env python3
"""
V38.0 Risk Engine Foundation

Implements:
- Pre-trade risk checks
- Maximum order notional
- Maximum per-symbol exposure
- Maximum gross exposure
- Maximum leverage
- Daily realized-loss limit
- Position-size limits
- Structured rejection reasons
- Immutable risk decision ledger
- SHA-256 audit hashes
- JSON CLI output

No broker network calls are performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Any, Sequence


VERSION = "38.0"


class RiskDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def decimal_value(value: str, field_name: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not number.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return number


def positive_decimal(value: str, field_name: str) -> Decimal:
    number = decimal_value(value, field_name)
    if number <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return number


def non_negative_decimal(value: str, field_name: str) -> Decimal:
    number = decimal_value(value, field_name)
    if number < 0:
        raise ValueError(f"{field_name} must be zero or greater")
    return number


def normalize_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


@dataclass(frozen=True)
class RiskLimits:
    max_order_notional: str
    max_symbol_exposure_pct: str
    max_gross_exposure_pct: str
    max_leverage: str
    max_daily_loss: str
    max_position_quantity: str


@dataclass(frozen=True)
class AccountRiskSnapshot:
    equity: str
    cash: str
    gross_exposure: str
    daily_realized_pnl: str
    symbol_exposures: dict[str, str]


@dataclass(frozen=True)
class OrderRiskRequest:
    symbol: str
    side: str
    quantity: str
    price: str


@dataclass(frozen=True)
class RiskCheck:
    check_id: str
    title: str
    status: str
    actual: str
    limit: str
    message: str


@dataclass(frozen=True)
class RiskDecisionRecord:
    schema_version: str
    version: str
    decision_id: str
    generated_at: str
    decision: str
    symbol: str
    side: str
    quantity: str
    price: str
    order_notional: str
    projected_symbol_exposure: str
    projected_gross_exposure: str
    projected_leverage: str
    rejection_reasons: list[str]
    checks: list[RiskCheck]
    network_used: bool
    decision_sha256: str


class RiskEngine:
    def __init__(self, limits: RiskLimits) -> None:
        self.max_order_notional = positive_decimal(
            limits.max_order_notional,
            "max_order_notional",
        )
        self.max_symbol_exposure_pct = positive_decimal(
            limits.max_symbol_exposure_pct,
            "max_symbol_exposure_pct",
        )
        self.max_gross_exposure_pct = positive_decimal(
            limits.max_gross_exposure_pct,
            "max_gross_exposure_pct",
        )
        self.max_leverage = positive_decimal(
            limits.max_leverage,
            "max_leverage",
        )
        self.max_daily_loss = positive_decimal(
            limits.max_daily_loss,
            "max_daily_loss",
        )
        self.max_position_quantity = positive_decimal(
            limits.max_position_quantity,
            "max_position_quantity",
        )
        self._ledger: list[RiskDecisionRecord] = []

    def evaluate(
        self,
        request: OrderRiskRequest,
        account: AccountRiskSnapshot,
    ) -> RiskDecisionRecord:
        symbol = request.symbol.strip().upper()
        side = request.side.strip().lower()

        if not symbol:
            raise ValueError("symbol is required")
        if side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")

        quantity = positive_decimal(request.quantity, "quantity")
        price = positive_decimal(request.price, "price")
        equity = positive_decimal(account.equity, "equity")
        cash = non_negative_decimal(account.cash, "cash")
        gross_exposure = non_negative_decimal(
            account.gross_exposure,
            "gross_exposure",
        )
        daily_realized_pnl = decimal_value(
            account.daily_realized_pnl,
            "daily_realized_pnl",
        )

        current_symbol_exposure = non_negative_decimal(
            account.symbol_exposures.get(symbol, "0"),
            f"symbol_exposure[{symbol}]",
        )

        order_notional = quantity * price
        if side == "buy":
            projected_symbol_exposure = (
                current_symbol_exposure + order_notional
            )
            projected_gross_exposure = (
                gross_exposure + order_notional
            )
        else:
            projected_symbol_exposure = max(
                Decimal("0"),
                current_symbol_exposure - order_notional,
            )
            projected_gross_exposure = max(
                Decimal("0"),
                gross_exposure - order_notional,
            )

        projected_leverage = projected_gross_exposure / equity
        symbol_exposure_pct = (
            projected_symbol_exposure / equity
        ) * Decimal("100")
        gross_exposure_pct = (
            projected_gross_exposure / equity
        ) * Decimal("100")

        checks: list[RiskCheck] = []
        reasons: list[str] = []

        def add_check(
            check_id: str,
            title: str,
            passed: bool,
            actual: Decimal,
            limit: Decimal,
            message_pass: str,
            message_fail: str,
        ) -> None:
            status = "PASS" if passed else "FAIL"
            message = message_pass if passed else message_fail
            checks.append(
                RiskCheck(
                    check_id=check_id,
                    title=title,
                    status=status,
                    actual=normalize_decimal(actual),
                    limit=normalize_decimal(limit),
                    message=message,
                )
            )
            if not passed:
                reasons.append(message_fail)

        add_check(
            "order.notional",
            "Maximum order notional",
            order_notional <= self.max_order_notional,
            order_notional,
            self.max_order_notional,
            "Order notional is within the configured limit.",
            "Order notional exceeds the configured maximum.",
        )

        add_check(
            "position.quantity",
            "Maximum position quantity",
            quantity <= self.max_position_quantity,
            quantity,
            self.max_position_quantity,
            "Order quantity is within the configured limit.",
            "Order quantity exceeds the configured maximum.",
        )

        add_check(
            "exposure.symbol",
            "Maximum symbol exposure",
            symbol_exposure_pct <= self.max_symbol_exposure_pct,
            symbol_exposure_pct,
            self.max_symbol_exposure_pct,
            "Projected symbol exposure is within the configured limit.",
            "Projected symbol exposure exceeds the configured maximum.",
        )

        add_check(
            "exposure.gross",
            "Maximum gross exposure",
            gross_exposure_pct <= self.max_gross_exposure_pct,
            gross_exposure_pct,
            self.max_gross_exposure_pct,
            "Projected gross exposure is within the configured limit.",
            "Projected gross exposure exceeds the configured maximum.",
        )

        add_check(
            "leverage.maximum",
            "Maximum leverage",
            projected_leverage <= self.max_leverage,
            projected_leverage,
            self.max_leverage,
            "Projected leverage is within the configured limit.",
            "Projected leverage exceeds the configured maximum.",
        )

        current_daily_loss = max(
            Decimal("0"),
            -daily_realized_pnl,
        )
        add_check(
            "loss.daily",
            "Daily loss limit",
            current_daily_loss < self.max_daily_loss,
            current_daily_loss,
            self.max_daily_loss,
            "Daily realized loss is below the configured limit.",
            "Daily realized loss limit has been reached or exceeded.",
        )

        if side == "buy":
            add_check(
                "cash.available",
                "Available cash",
                order_notional <= cash,
                order_notional,
                cash,
                "Available cash is sufficient for the order.",
                "Available cash is insufficient for the order.",
            )
        else:
            add_check(
                "sell.exposure",
                "Sell exposure availability",
                order_notional <= current_symbol_exposure,
                order_notional,
                current_symbol_exposure,
                "Current symbol exposure is sufficient for the sell order.",
                "Sell order exceeds the current symbol exposure.",
            )

        decision = (
            RiskDecision.APPROVE
            if not reasons
            else RiskDecision.REJECT
        )

        core = {
            "schema_version": "v38.0.risk_decision.1",
            "version": VERSION,
            "decision_id": f"risk-{uuid.uuid4().hex}",
            "generated_at": utc_now(),
            "decision": decision.value,
            "symbol": symbol,
            "side": side,
            "quantity": normalize_decimal(quantity),
            "price": normalize_decimal(price),
            "order_notional": normalize_decimal(order_notional),
            "projected_symbol_exposure": normalize_decimal(
                projected_symbol_exposure
            ),
            "projected_gross_exposure": normalize_decimal(
                projected_gross_exposure
            ),
            "projected_leverage": normalize_decimal(
                projected_leverage
            ),
            "rejection_reasons": reasons,
            "checks": checks,
            "network_used": False,
        }
        record = RiskDecisionRecord(
            **core,
            decision_sha256=canonical_hash({
                **core,
                "checks": [asdict(check) for check in checks],
            }),
        )
        self._ledger.append(record)
        return record

    def ledger(self) -> list[RiskDecisionRecord]:
        return list(self._ledger)

    def export(self) -> dict[str, Any]:
        return {
            "schema_version": "v38.0.risk_ledger.1",
            "version": VERSION,
            "decision_count": len(self._ledger),
            "decisions": [asdict(item) for item in self._ledger],
            "network_used": False,
        }


def default_limits() -> RiskLimits:
    return RiskLimits(
        max_order_notional="25000",
        max_symbol_exposure_pct="25",
        max_gross_exposure_pct="100",
        max_leverage="1",
        max_daily_loss="2000",
        max_position_quantity="1000",
    )


def demo_risk_engine(
    *,
    symbol: str,
    side: str,
    quantity: str,
    price: str,
    equity: str,
    cash: str,
    gross_exposure: str,
    symbol_exposure: str,
    daily_realized_pnl: str,
) -> dict[str, Any]:
    engine = RiskEngine(default_limits())
    decision = engine.evaluate(
        OrderRiskRequest(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
        ),
        AccountRiskSnapshot(
            equity=equity,
            cash=cash,
            gross_exposure=gross_exposure,
            daily_realized_pnl=daily_realized_pnl,
            symbol_exposures={symbol.upper(): symbol_exposure},
        ),
    )
    return {
        "schema_version": "v38.0.risk_demo.1",
        "version": VERSION,
        "decision": asdict(decision),
        "ledger": engine.export(),
        "network_used": False,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="V38.0 Risk Engine Foundation"
    )
    p.add_argument("--symbol", default="AAPL")
    p.add_argument("--side", choices=["buy", "sell"], default="buy")
    p.add_argument("--quantity", default="50")
    p.add_argument("--price", default="200")
    p.add_argument("--equity", default="100000")
    p.add_argument("--cash", default="50000")
    p.add_argument("--gross-exposure", default="30000")
    p.add_argument("--symbol-exposure", default="10000")
    p.add_argument("--daily-realized-pnl", default="-500")
    p.add_argument(
        "--output",
        default="release/v38/audit/risk_engine_result_v38_0.json",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    payload = demo_risk_engine(
        symbol=args.symbol,
        side=args.side,
        quantity=args.quantity,
        price=args.price,
        equity=args.equity,
        cash=args.cash,
        gross_exposure=args.gross_exposure,
        symbol_exposure=args.symbol_exposure,
        daily_realized_pnl=args.daily_realized_pnl,
    )
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
