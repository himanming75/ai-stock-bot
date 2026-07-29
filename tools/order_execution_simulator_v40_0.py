#!/usr/bin/env python3
"""
V40.0 Order Execution Simulator

Offline integration simulator that connects:
- Pre-trade risk approval/rejection
- Order lifecycle
- Partial and full fills
- Position accounting
- Portfolio snapshot updates
- Execution receipts
- Immutable audit trail
- SHA-256 hashes

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


VERSION = "40.0"


class ExecutionStatus(str, Enum):
    REJECTED_RISK = "rejected_risk"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"


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


def dec(value: str, name: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not number.is_finite():
        raise ValueError(f"{name} must be finite")
    return number


def pos(value: str, name: str) -> Decimal:
    number = dec(value, name)
    if number <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return number


def nonneg(value: str, name: str) -> Decimal:
    number = dec(value, name)
    if number < 0:
        raise ValueError(f"{name} must be zero or greater")
    return number


def norm(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


@dataclass(frozen=True)
class RiskLimits:
    max_order_notional: str = "25000"
    max_symbol_exposure_pct: str = "25"
    max_gross_exposure_pct: str = "100"
    max_daily_loss: str = "2000"


@dataclass(frozen=True)
class AccountState:
    cash: str
    equity: str
    gross_exposure: str
    symbol_exposure: str
    daily_realized_pnl: str


@dataclass(frozen=True)
class ExecutionRequest:
    symbol: str
    side: str
    quantity: str
    price: str
    first_fill_quantity: str
    second_fill_quantity: str | None = None
    second_fill_price: str | None = None


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    generated_at: str
    stage: str
    status: str
    message: str
    details: dict[str, Any]
    event_sha256: str


@dataclass(frozen=True)
class ExecutionReceipt:
    schema_version: str
    version: str
    execution_id: str
    order_id: str
    symbol: str
    side: str
    requested_quantity: str
    filled_quantity: str
    remaining_quantity: str
    average_fill_price: str | None
    status: str
    risk_decision: str
    rejection_reasons: list[str]
    position_quantity: str
    position_average_price: str | None
    portfolio_cash: str
    portfolio_market_value: str
    portfolio_equity: str
    event_count: int
    network_used: bool
    generated_at: str
    receipt_sha256: str


class OrderExecutionSimulator:
    def __init__(
        self,
        *,
        account: AccountState,
        limits: RiskLimits | None = None,
    ) -> None:
        self.account = account
        self.limits = limits or RiskLimits()
        self._events: list[AuditEvent] = []

    def _event(
        self,
        *,
        stage: str,
        status: str,
        message: str,
        details: dict[str, Any],
    ) -> AuditEvent:
        core = {
            "event_id": f"evt-{uuid.uuid4().hex}",
            "generated_at": utc_now(),
            "stage": stage,
            "status": status,
            "message": message,
            "details": details,
        }
        event = AuditEvent(
            **core,
            event_sha256=canonical_hash(core),
        )
        self._events.append(event)
        return event

    def _risk_check(
        self,
        request: ExecutionRequest,
    ) -> tuple[str, list[str], dict[str, str]]:
        quantity = pos(request.quantity, "quantity")
        price = pos(request.price, "price")
        equity = pos(self.account.equity, "equity")
        cash = nonneg(self.account.cash, "cash")
        gross = nonneg(self.account.gross_exposure, "gross_exposure")
        symbol_exposure = nonneg(
            self.account.symbol_exposure,
            "symbol_exposure",
        )
        daily_pnl = dec(
            self.account.daily_realized_pnl,
            "daily_realized_pnl",
        )

        max_notional = pos(
            self.limits.max_order_notional,
            "max_order_notional",
        )
        max_symbol_pct = pos(
            self.limits.max_symbol_exposure_pct,
            "max_symbol_exposure_pct",
        )
        max_gross_pct = pos(
            self.limits.max_gross_exposure_pct,
            "max_gross_exposure_pct",
        )
        max_daily_loss = pos(
            self.limits.max_daily_loss,
            "max_daily_loss",
        )

        notional = quantity * price
        if request.side == "buy":
            projected_symbol = symbol_exposure + notional
            projected_gross = gross + notional
        else:
            projected_symbol = max(
                Decimal("0"),
                symbol_exposure - notional,
            )
            projected_gross = max(
                Decimal("0"),
                gross - notional,
            )

        symbol_pct = projected_symbol / equity * Decimal("100")
        gross_pct = projected_gross / equity * Decimal("100")
        daily_loss = max(Decimal("0"), -daily_pnl)

        reasons: list[str] = []
        if notional > max_notional:
            reasons.append(
                "Order notional exceeds the configured maximum."
            )
        if symbol_pct > max_symbol_pct:
            reasons.append(
                "Projected symbol exposure exceeds the configured maximum."
            )
        if gross_pct > max_gross_pct:
            reasons.append(
                "Projected gross exposure exceeds the configured maximum."
            )
        if daily_loss >= max_daily_loss:
            reasons.append(
                "Daily realized loss limit has been reached or exceeded."
            )
        if request.side == "buy" and notional > cash:
            reasons.append(
                "Available cash is insufficient for the order."
            )
        if request.side == "sell" and notional > symbol_exposure:
            reasons.append(
                "Sell order exceeds the current symbol exposure."
            )

        decision = "approve" if not reasons else "reject"
        details = {
            "order_notional": norm(notional),
            "projected_symbol_exposure": norm(projected_symbol),
            "projected_gross_exposure": norm(projected_gross),
            "projected_symbol_exposure_pct": norm(symbol_pct),
            "projected_gross_exposure_pct": norm(gross_pct),
        }
        return decision, reasons, details

    def execute(self, request: ExecutionRequest) -> ExecutionReceipt:
        symbol = request.symbol.strip().upper()
        side = request.side.strip().lower()
        if not symbol:
            raise ValueError("symbol is required")
        if side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")

        requested_qty = pos(request.quantity, "quantity")
        order_price = pos(request.price, "price")
        first_qty = pos(
            request.first_fill_quantity,
            "first_fill_quantity",
        )
        second_qty = (
            pos(request.second_fill_quantity, "second_fill_quantity")
            if request.second_fill_quantity is not None
            else Decimal("0")
        )
        second_price = (
            pos(request.second_fill_price, "second_fill_price")
            if request.second_fill_price is not None
            else order_price
        )

        if first_qty + second_qty > requested_qty:
            raise ValueError(
                "fill quantities exceed requested quantity"
            )

        execution_id = f"exec-{uuid.uuid4().hex}"
        order_id = f"order-{uuid.uuid4().hex}"

        self._event(
            stage="order_created",
            status="PASS",
            message="Order request created.",
            details={
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "quantity": norm(requested_qty),
                "price": norm(order_price),
            },
        )

        risk_decision, reasons, risk_details = self._risk_check(
            ExecutionRequest(
                symbol=symbol,
                side=side,
                quantity=norm(requested_qty),
                price=norm(order_price),
                first_fill_quantity=norm(first_qty),
                second_fill_quantity=(
                    norm(second_qty) if second_qty else None
                ),
                second_fill_price=(
                    norm(second_price)
                    if request.second_fill_price is not None
                    else None
                ),
            )
        )

        self._event(
            stage="risk_check",
            status="PASS" if risk_decision == "approve" else "FAIL",
            message=(
                "Risk checks passed."
                if risk_decision == "approve"
                else "Risk checks rejected the order."
            ),
            details={
                **risk_details,
                "rejection_reasons": reasons,
            },
        )

        cash = nonneg(self.account.cash, "cash")
        current_market_value = nonneg(
            self.account.gross_exposure,
            "gross_exposure",
        )

        if risk_decision == "reject":
            return self._build_receipt(
                execution_id=execution_id,
                order_id=order_id,
                symbol=symbol,
                side=side,
                requested_qty=requested_qty,
                filled_qty=Decimal("0"),
                average_fill_price=None,
                status=ExecutionStatus.REJECTED_RISK,
                risk_decision=risk_decision,
                reasons=reasons,
                position_qty=Decimal("0"),
                position_avg=None,
                cash=cash,
                market_value=current_market_value,
            )

        self._event(
            stage="order_validated",
            status="PASS",
            message="Order validation passed.",
            details={},
        )
        self._event(
            stage="order_routed",
            status="PASS",
            message="Order routed to offline paper execution.",
            details={"network_used": False},
        )
        self._event(
            stage="order_accepted",
            status="PASS",
            message="Offline paper broker accepted the order.",
            details={},
        )

        fills: list[tuple[Decimal, Decimal]] = []
        if first_qty:
            fills.append((first_qty, order_price))
        if second_qty:
            fills.append((second_qty, second_price))

        filled_qty = Decimal("0")
        fill_notional = Decimal("0")

        for index, (fill_qty, fill_price) in enumerate(
            fills,
            start=1,
        ):
            filled_qty += fill_qty
            fill_notional += fill_qty * fill_price
            self._event(
                stage="fill",
                status="PASS",
                message=(
                    "Order fully filled."
                    if filled_qty == requested_qty
                    else "Order partially filled."
                ),
                details={
                    "trade_id": f"trade-{index:03d}",
                    "fill_quantity": norm(fill_qty),
                    "fill_price": norm(fill_price),
                    "cumulative_filled_quantity": norm(filled_qty),
                    "remaining_quantity": norm(
                        requested_qty - filled_qty
                    ),
                },
            )

        average_fill_price = (
            fill_notional / filled_qty
            if filled_qty > 0
            else None
        )

        position_qty = filled_qty
        position_avg = average_fill_price

        self._event(
            stage="position_update",
            status="PASS",
            message="Position updated from accepted fills.",
            details={
                "position_quantity": norm(position_qty),
                "position_average_price": (
                    norm(position_avg)
                    if position_avg is not None
                    else None
                ),
            },
        )

        if side == "buy":
            cash_after = cash - fill_notional
            market_value_after = current_market_value + fill_notional
        else:
            cash_after = cash + fill_notional
            market_value_after = max(
                Decimal("0"),
                current_market_value - fill_notional,
            )

        equity_after = cash_after + market_value_after

        self._event(
            stage="portfolio_update",
            status="PASS",
            message="Portfolio snapshot updated.",
            details={
                "cash": norm(cash_after),
                "market_value": norm(market_value_after),
                "equity": norm(equity_after),
            },
        )

        status = (
            ExecutionStatus.FILLED
            if filled_qty == requested_qty
            else ExecutionStatus.PARTIALLY_FILLED
        )

        return self._build_receipt(
            execution_id=execution_id,
            order_id=order_id,
            symbol=symbol,
            side=side,
            requested_qty=requested_qty,
            filled_qty=filled_qty,
            average_fill_price=average_fill_price,
            status=status,
            risk_decision=risk_decision,
            reasons=[],
            position_qty=position_qty,
            position_avg=position_avg,
            cash=cash_after,
            market_value=market_value_after,
        )

    def _build_receipt(
        self,
        *,
        execution_id: str,
        order_id: str,
        symbol: str,
        side: str,
        requested_qty: Decimal,
        filled_qty: Decimal,
        average_fill_price: Decimal | None,
        status: ExecutionStatus,
        risk_decision: str,
        reasons: list[str],
        position_qty: Decimal,
        position_avg: Decimal | None,
        cash: Decimal,
        market_value: Decimal,
    ) -> ExecutionReceipt:
        equity = cash + market_value
        core = {
            "schema_version": "v40.0.execution_receipt.1",
            "version": VERSION,
            "execution_id": execution_id,
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "requested_quantity": norm(requested_qty),
            "filled_quantity": norm(filled_qty),
            "remaining_quantity": norm(
                requested_qty - filled_qty
            ),
            "average_fill_price": (
                norm(average_fill_price)
                if average_fill_price is not None
                else None
            ),
            "status": status.value,
            "risk_decision": risk_decision,
            "rejection_reasons": reasons,
            "position_quantity": norm(position_qty),
            "position_average_price": (
                norm(position_avg)
                if position_avg is not None
                else None
            ),
            "portfolio_cash": norm(cash),
            "portfolio_market_value": norm(market_value),
            "portfolio_equity": norm(equity),
            "event_count": len(self._events),
            "network_used": False,
            "generated_at": utc_now(),
        }
        return ExecutionReceipt(
            **core,
            receipt_sha256=canonical_hash(core),
        )

    def audit_log(self) -> list[AuditEvent]:
        return list(self._events)

    def export(
        self,
        receipt: ExecutionReceipt,
    ) -> dict[str, Any]:
        return {
            "schema_version": "v40.0.execution_simulation.1",
            "version": VERSION,
            "receipt": asdict(receipt),
            "audit_log": [
                asdict(event) for event in self.audit_log()
            ],
            "network_used": False,
        }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="V40.0 Order Execution Simulator"
    )
    p.add_argument("--symbol", default="AAPL")
    p.add_argument("--side", choices=["buy", "sell"], default="buy")
    p.add_argument("--quantity", default="10")
    p.add_argument("--price", default="200")
    p.add_argument("--first-fill-quantity", default="4")
    p.add_argument("--second-fill-quantity", default="6")
    p.add_argument("--second-fill-price", default="210")
    p.add_argument("--cash", default="50000")
    p.add_argument("--equity", default="100000")
    p.add_argument("--gross-exposure", default="30000")
    p.add_argument("--symbol-exposure", default="10000")
    p.add_argument("--daily-realized-pnl", default="-500")
    p.add_argument(
        "--output",
        default="release/v40/audit/order_execution_result_v40_0.json",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    simulator = OrderExecutionSimulator(
        account=AccountState(
            cash=args.cash,
            equity=args.equity,
            gross_exposure=args.gross_exposure,
            symbol_exposure=args.symbol_exposure,
            daily_realized_pnl=args.daily_realized_pnl,
        )
    )
    receipt = simulator.execute(
        ExecutionRequest(
            symbol=args.symbol,
            side=args.side,
            quantity=args.quantity,
            price=args.price,
            first_fill_quantity=args.first_fill_quantity,
            second_fill_quantity=args.second_fill_quantity,
            second_fill_price=args.second_fill_price,
        )
    )
    payload = simulator.export(receipt)

    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
