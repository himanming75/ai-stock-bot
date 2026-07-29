#!/usr/bin/env python3
"""
V49.0 Paper Portfolio Reconciliation Foundation

Consumes a V48 paper-fill simulation result and deterministically reconciles
cash, positions, average cost, realized P&L, unrealized P&L, market value,
and total equity.

Offline only:
- no broker connection
- no market-data request
- no network use
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Sequence

VERSION = "49.0"
MONEY_Q = Decimal("0.0001")
QTY_Q = Decimal("0.000001")


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def d(value: Any, *, field: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not parsed.is_finite():
        raise ValueError(f"{field} must be finite")
    return parsed


def q_money(value: Decimal) -> str:
    return format(value.quantize(MONEY_Q, rounding=ROUND_HALF_UP), "f")


def q_qty(value: Decimal) -> str:
    value = value.quantize(QTY_Q, rounding=ROUND_HALF_UP)
    text = format(value, "f").rstrip("0").rstrip(".")
    return text or "0"


def parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class FillInput:
    fill_id: str
    broker_order_id: str
    symbol: str
    side: str
    fill_quantity: str
    fill_price: str
    gross_notional: str
    commission: str
    slippage_bps: str
    reference_price: str
    event_at: str
    network_used: bool
    fill_sha256: str


@dataclass(frozen=True)
class FillOrderInput:
    broker_order_id: str
    child_order_id: str
    symbol: str
    side: str
    requested_quantity: str
    filled_quantity: str
    remaining_quantity: str
    weighted_average_fill_price: str | None
    gross_notional: str
    total_commission: str
    final_status: str
    fills: list[dict[str, Any]]
    order_result_sha256: str


@dataclass(frozen=True)
class FillSimulationInput:
    schema_version: str
    version: str
    status: str
    decision: str
    gateway_sha256: str
    order_count: int
    fill_event_count: int
    fully_filled_count: int
    partially_filled_count: int
    unfilled_count: int
    total_filled_quantity: str
    total_gross_notional: str
    total_commission: str
    orders: list[dict[str, Any]]
    ledger: list[dict[str, Any]]
    rejection_reasons: list[str]
    network_used: bool
    simulation_sha256: str


@dataclass(frozen=True)
class PositionSnapshot:
    symbol: str
    quantity: str
    average_cost: str
    market_price: str
    market_value: str
    cost_basis: str
    unrealized_pnl: str
    realized_pnl: str
    total_commission: str
    position_sha256: str


@dataclass(frozen=True)
class ReconciliationLedgerEntry:
    sequence: int
    event_type: str
    symbol: str
    fill_id: str
    side: str
    quantity: str
    price: str
    commission: str
    cash_before: str
    cash_after: str
    position_quantity_before: str
    position_quantity_after: str
    average_cost_before: str
    average_cost_after: str
    realized_pnl_delta: str
    event_at: str
    previous_entry_sha256: str
    payload_sha256: str
    entry_sha256: str


@dataclass(frozen=True)
class PortfolioReconciliationResult:
    schema_version: str
    version: str
    status: str
    decision: str
    simulation_sha256: str
    starting_cash: str
    ending_cash: str
    total_market_value: str
    total_cost_basis: str
    total_realized_pnl: str
    total_unrealized_pnl: str
    total_commission: str
    total_equity: str
    position_count: int
    positions: list[dict[str, Any]]
    ledger: list[dict[str, Any]]
    rejection_reasons: list[str]
    network_used: bool
    reconciliation_sha256: str


class PaperPortfolioReconciler:
    def __init__(
        self,
        *,
        mode: str = "paper",
        enable_live: bool = False,
        reference_time: str | None = None,
        allow_short: bool = False,
    ) -> None:
        if mode not in {"replay", "paper", "live"}:
            raise ValueError("mode must be replay, paper, or live")
        self.mode = mode
        self.enable_live = enable_live
        self.reference_time = (
            parse_timestamp(reference_time)
            if reference_time
            else datetime.now(timezone.utc)
        )
        self.allow_short = allow_short
        self.ledger: list[ReconciliationLedgerEntry] = []

    def _live_gate(self) -> None:
        if self.mode == "live":
            if not self.enable_live:
                raise PermissionError("live mode requires --enable-live")
            raise NotImplementedError(
                "live portfolio transport is intentionally not implemented in V49.0"
            )

    @staticmethod
    def _simulation_hash_payload(sim: FillSimulationInput) -> dict[str, Any]:
        return {
            "schema_version": sim.schema_version,
            "version": sim.version,
            "status": sim.status,
            "decision": sim.decision,
            "gateway_sha256": sim.gateway_sha256,
            "order_count": sim.order_count,
            "fill_event_count": sim.fill_event_count,
            "fully_filled_count": sim.fully_filled_count,
            "partially_filled_count": sim.partially_filled_count,
            "unfilled_count": sim.unfilled_count,
            "total_filled_quantity": sim.total_filled_quantity,
            "total_gross_notional": sim.total_gross_notional,
            "total_commission": sim.total_commission,
            "orders": sim.orders,
            "ledger": sim.ledger,
            "rejection_reasons": sim.rejection_reasons,
            "network_used": sim.network_used,
        }

    @staticmethod
    def _fill_hash_payload(fill: FillInput) -> dict[str, Any]:
        return {
            "fill_id": fill.fill_id,
            "broker_order_id": fill.broker_order_id,
            "symbol": fill.symbol,
            "side": fill.side,
            "fill_quantity": fill.fill_quantity,
            "fill_price": fill.fill_price,
            "gross_notional": fill.gross_notional,
            "commission": fill.commission,
            "slippage_bps": fill.slippage_bps,
            "reference_price": fill.reference_price,
            "event_at": fill.event_at,
            "network_used": fill.network_used,
        }

    @staticmethod
    def _order_hash_payload(order: FillOrderInput) -> dict[str, Any]:
        return {
            "broker_order_id": order.broker_order_id,
            "child_order_id": order.child_order_id,
            "symbol": order.symbol,
            "side": order.side,
            "requested_quantity": order.requested_quantity,
            "filled_quantity": order.filled_quantity,
            "remaining_quantity": order.remaining_quantity,
            "weighted_average_fill_price": order.weighted_average_fill_price,
            "gross_notional": order.gross_notional,
            "total_commission": order.total_commission,
            "final_status": order.final_status,
            "fills": order.fills,
        }

    def _event_time(self, offset: int) -> str:
        dt = self.reference_time + timedelta(microseconds=offset)
        return dt.isoformat().replace("+00:00", "Z")

    def _append_ledger(
        self,
        *,
        event_type: str,
        symbol: str,
        fill_id: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        commission: Decimal,
        cash_before: Decimal,
        cash_after: Decimal,
        qty_before: Decimal,
        qty_after: Decimal,
        avg_before: Decimal,
        avg_after: Decimal,
        realized_delta: Decimal,
        event_at: str,
    ) -> None:
        previous = self.ledger[-1].entry_sha256 if self.ledger else "GENESIS"
        payload = {
            "event_type": event_type,
            "symbol": symbol,
            "fill_id": fill_id,
            "side": side,
            "quantity": q_qty(quantity),
            "price": q_money(price),
            "commission": q_money(commission),
            "cash_before": q_money(cash_before),
            "cash_after": q_money(cash_after),
            "position_quantity_before": q_qty(qty_before),
            "position_quantity_after": q_qty(qty_after),
            "average_cost_before": q_money(avg_before),
            "average_cost_after": q_money(avg_after),
            "realized_pnl_delta": q_money(realized_delta),
            "event_at": event_at,
        }
        payload_hash = canonical_hash(payload)
        core = {
            "sequence": len(self.ledger) + 1,
            **payload,
            "previous_entry_sha256": previous,
            "payload_sha256": payload_hash,
        }
        self.ledger.append(
            ReconciliationLedgerEntry(
                **core,
                entry_sha256=canonical_hash(core),
            )
        )

    def reconcile(
        self,
        simulation: FillSimulationInput,
        *,
        starting_cash: str,
        market_prices: dict[str, str],
    ) -> PortfolioReconciliationResult:
        self._live_gate()
        reasons: list[str] = []

        expected_sim_hash = canonical_hash(
            self._simulation_hash_payload(simulation)
        )
        if simulation.status != "PASS":
            reasons.append("V48 simulation status must be PASS.")
        if simulation.decision != "simulate":
            reasons.append("V48 simulation decision must be simulate.")
        if simulation.network_used is not False:
            reasons.append("V48 simulation must report network_used=false.")
        if simulation.rejection_reasons:
            reasons.append("V48 simulation contains rejection reasons.")
        if simulation.order_count != len(simulation.orders):
            reasons.append("V48 order_count does not match orders length.")
        if expected_sim_hash != simulation.simulation_sha256:
            reasons.append("V48 simulation SHA-256 verification failed.")

        cash = d(starting_cash, field="starting_cash")
        if cash < 0:
            reasons.append("starting_cash must be non-negative.")
        start_cash = cash

        normalized_prices: dict[str, Decimal] = {}
        for symbol, value in market_prices.items():
            price = d(value, field=f"market_price[{symbol}]")
            if price <= 0:
                reasons.append(f"market price must be positive: {symbol}")
            normalized_prices[symbol.upper()] = price

        states: dict[str, dict[str, Decimal]] = {}
        total_commission = Decimal("0")
        processed_fills = 0

        if not reasons:
            for order_raw in simulation.orders:
                try:
                    order = FillOrderInput(**order_raw)
                except TypeError as exc:
                    reasons.append(f"invalid V48 order shape: {exc}")
                    break

                expected_order_hash = canonical_hash(
                    self._order_hash_payload(order)
                )
                if expected_order_hash != order.order_result_sha256:
                    reasons.append(
                        f"order result SHA-256 verification failed: {order.broker_order_id}"
                    )
                    break

                fills_qty = Decimal("0")
                fills_gross = Decimal("0")
                fills_commission = Decimal("0")

                for raw_fill in order.fills:
                    try:
                        fill = FillInput(**raw_fill)
                    except TypeError as exc:
                        reasons.append(f"invalid fill shape: {exc}")
                        break

                    if fill.network_used is not False:
                        reasons.append(
                            f"fill reports network_used=true: {fill.fill_id}"
                        )
                        break

                    if canonical_hash(self._fill_hash_payload(fill)) != fill.fill_sha256:
                        reasons.append(
                            f"fill SHA-256 verification failed: {fill.fill_id}"
                        )
                        break

                    symbol = fill.symbol.upper()
                    side = fill.side.lower()
                    qty = d(fill.fill_quantity, field="fill_quantity")
                    price = d(fill.fill_price, field="fill_price")
                    gross = d(fill.gross_notional, field="gross_notional")
                    commission = d(fill.commission, field="commission")

                    if qty <= 0:
                        reasons.append(f"fill quantity must be positive: {fill.fill_id}")
                        break
                    if price <= 0:
                        reasons.append(f"fill price must be positive: {fill.fill_id}")
                        break
                    if commission < 0:
                        reasons.append(f"commission must be non-negative: {fill.fill_id}")
                        break
                    if q_money(qty * price) != q_money(gross):
                        reasons.append(f"gross notional mismatch: {fill.fill_id}")
                        break
                    if side not in {"buy", "sell"}:
                        reasons.append(f"fill side must be buy or sell: {fill.fill_id}")
                        break

                    state = states.setdefault(
                        symbol,
                        {
                            "quantity": Decimal("0"),
                            "average_cost": Decimal("0"),
                            "realized_pnl": Decimal("0"),
                            "commission": Decimal("0"),
                        },
                    )
                    qty_before = state["quantity"]
                    avg_before = state["average_cost"]
                    cash_before = cash
                    realized_delta = Decimal("0")

                    if side == "buy":
                        if qty_before < 0 and not self.allow_short:
                            reasons.append(
                                f"short-cover accounting requires --allow-short: {symbol}"
                            )
                            break
                        qty_after = qty_before + qty
                        if qty_before >= 0:
                            avg_after = (
                                ((qty_before * avg_before) + gross + commission)
                                / qty_after
                            )
                        else:
                            cover_qty = min(qty, -qty_before)
                            realized_delta = (
                                (avg_before - price) * cover_qty - commission
                            )
                            if qty_after < 0:
                                avg_after = avg_before
                            elif qty_after == 0:
                                avg_after = Decimal("0")
                            else:
                                avg_after = (
                                    (qty - cover_qty) * price + commission
                                ) / qty_after
                        cash_after = cash_before - gross - commission
                    else:
                        if qty_before < qty and not self.allow_short:
                            reasons.append(
                                f"sell quantity exceeds long position: {symbol}"
                            )
                            break
                        qty_after = qty_before - qty
                        if qty_before > 0:
                            closing_qty = min(qty, qty_before)
                            realized_delta = (
                                (price - avg_before) * closing_qty - commission
                            )
                            if qty_after > 0:
                                avg_after = avg_before
                            elif qty_after == 0:
                                avg_after = Decimal("0")
                            else:
                                avg_after = price
                        else:
                            avg_after = (
                                ((-qty_before * avg_before) + gross - commission)
                                / (-qty_after)
                            )
                        cash_after = cash_before + gross - commission

                    state["quantity"] = qty_after
                    state["average_cost"] = avg_after
                    state["realized_pnl"] += realized_delta
                    state["commission"] += commission
                    cash = cash_after
                    total_commission += commission
                    fills_qty += qty
                    fills_gross += gross
                    fills_commission += commission
                    processed_fills += 1

                    self._append_ledger(
                        event_type="FILL_RECONCILED",
                        symbol=symbol,
                        fill_id=fill.fill_id,
                        side=side,
                        quantity=qty,
                        price=price,
                        commission=commission,
                        cash_before=cash_before,
                        cash_after=cash_after,
                        qty_before=qty_before,
                        qty_after=qty_after,
                        avg_before=avg_before,
                        avg_after=avg_after,
                        realized_delta=realized_delta,
                        event_at=self._event_time(processed_fills),
                    )

                if reasons:
                    break

                if q_qty(fills_qty) != q_qty(
                    d(order.filled_quantity, field="filled_quantity")
                ):
                    reasons.append(
                        f"order filled quantity mismatch: {order.broker_order_id}"
                    )
                    break
                if q_money(fills_gross) != q_money(
                    d(order.gross_notional, field="gross_notional")
                ):
                    reasons.append(
                        f"order gross notional mismatch: {order.broker_order_id}"
                    )
                    break
                if q_money(fills_commission) != q_money(
                    d(order.total_commission, field="total_commission")
                ):
                    reasons.append(
                        f"order commission mismatch: {order.broker_order_id}"
                    )
                    break

        positions: list[PositionSnapshot] = []
        total_market_value = Decimal("0")
        total_cost_basis = Decimal("0")
        total_realized = Decimal("0")
        total_unrealized = Decimal("0")

        if not reasons:
            for symbol in sorted(states):
                state = states[symbol]
                qty = state["quantity"]
                avg = state["average_cost"]
                realized = state["realized_pnl"]
                commission = state["commission"]
                market_price = normalized_prices.get(symbol)
                if market_price is None:
                    reasons.append(f"missing market price: {symbol}")
                    break

                market_value = qty * market_price
                cost_basis = qty * avg
                if qty >= 0:
                    unrealized = (market_price - avg) * qty
                else:
                    unrealized = (avg - market_price) * (-qty)

                core = {
                    "symbol": symbol,
                    "quantity": q_qty(qty),
                    "average_cost": q_money(avg),
                    "market_price": q_money(market_price),
                    "market_value": q_money(market_value),
                    "cost_basis": q_money(cost_basis),
                    "unrealized_pnl": q_money(unrealized),
                    "realized_pnl": q_money(realized),
                    "total_commission": q_money(commission),
                }
                positions.append(
                    PositionSnapshot(
                        **core,
                        position_sha256=canonical_hash(core),
                    )
                )
                total_market_value += market_value
                total_cost_basis += cost_basis
                total_realized += realized
                total_unrealized += unrealized

        status = "PASS" if not reasons else "FAIL"
        decision = "reconcile" if not reasons else "reject"
        core = {
            "schema_version": "v49.0.paper_portfolio_reconciliation.1",
            "version": VERSION,
            "status": status,
            "decision": decision,
            "simulation_sha256": simulation.simulation_sha256,
            "starting_cash": q_money(start_cash),
            "ending_cash": q_money(cash),
            "total_market_value": q_money(total_market_value),
            "total_cost_basis": q_money(total_cost_basis),
            "total_realized_pnl": q_money(total_realized),
            "total_unrealized_pnl": q_money(total_unrealized),
            "total_commission": q_money(total_commission),
            "total_equity": q_money(cash + total_market_value),
            "position_count": len(positions),
            "positions": [asdict(p) for p in positions],
            "ledger": [asdict(x) for x in self.ledger],
            "rejection_reasons": reasons,
            "network_used": False,
        }
        return PortfolioReconciliationResult(
            **core,
            reconciliation_sha256=canonical_hash(core),
        )

    @staticmethod
    def export(path: Path, result: PortfolioReconciliationResult) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "v49.0.paper_portfolio_reconciliation_export.1",
            "version": VERSION,
            "result": asdict(result),
            "network_used": False,
        }
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def load_simulation(path: Path) -> FillSimulationInput:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("result", payload)
    return FillSimulationInput(**raw)


def parse_market_prices(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise ValueError(
                "market prices must use SYMBOL=PRICE format"
            )
        symbol, price = item.split("=", 1)
        symbol = symbol.strip().upper()
        if not symbol:
            raise ValueError("market price symbol cannot be empty")
        result[symbol] = price.strip()
    if not result:
        raise ValueError("at least one market price is required")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="V49.0 Paper Portfolio Reconciliation Foundation"
    )
    parser.add_argument(
        "--input",
        default="release/v48/audit/paper_fill_simulation_result_v48_0.json",
    )
    parser.add_argument("--starting-cash", required=True)
    parser.add_argument(
        "--market-prices",
        required=True,
        help="Comma-separated prices, e.g. AAPL=205,MSFT=430",
    )
    parser.add_argument(
        "--mode",
        choices=["replay", "paper", "live"],
        default="paper",
    )
    parser.add_argument("--enable-live", action="store_true")
    parser.add_argument("--allow-short", action="store_true")
    parser.add_argument("--reference-time")
    parser.add_argument(
        "--output",
        default=(
            "release/v49/audit/"
            "paper_portfolio_reconciliation_result_v49_0.json"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output)
    try:
        reconciler = PaperPortfolioReconciler(
            mode=args.mode,
            enable_live=args.enable_live,
            reference_time=args.reference_time,
            allow_short=args.allow_short,
        )
        simulation = load_simulation(Path(args.input))
        result = reconciler.reconcile(
            simulation,
            starting_cash=args.starting_cash,
            market_prices=parse_market_prices(args.market_prices),
        )
        reconciler.export(output, result)
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
        return 0 if result.status == "PASS" else 1
    except (
        TypeError,
        ValueError,
        PermissionError,
        NotImplementedError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        error = {
            "schema_version": "v49.0.paper_portfolio_reconciliation_error.1",
            "version": VERSION,
            "status": "FAIL",
            "error": str(exc),
            "network_used": False,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(error, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(json.dumps(error, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
