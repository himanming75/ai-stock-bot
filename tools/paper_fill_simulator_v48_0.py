#!/usr/bin/env python3
"""
V48.0 Paper Fill Simulator Foundation

Consumes a V47 paper-broker gateway result and simulates deterministic,
offline order fills.

No live broker connection, network transport, or market-data request is
implemented.

Features:
- V47 gateway status, decision, integrity, and network verification
- market and limit-order fill evaluation
- configurable slippage in basis points
- configurable per-share commission and minimum commission
- partial fills across one or more liquidity slices
- weighted-average fill price
- remaining quantity and final order status
- fill-event ledger with SHA-256 hash chaining
- deterministic replay with fixed reference time
- explicit live-mode safety gate
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

VERSION = "48.0"
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
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result


def q_money(value: Decimal) -> str:
    return format(value.quantize(MONEY_Q, rounding=ROUND_HALF_UP), "f")


def q_qty(value: Decimal) -> str:
    normalized = value.quantize(QTY_Q, rounding=ROUND_HALF_UP)
    text = format(normalized, "f")
    text = text.rstrip("0").rstrip(".")
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
class BrokerOrderInput:
    accepted_at: str
    broker_order_id: str
    broker_order_sha256: str
    child_order_id: str
    limit_price: str | None
    network_used: bool
    order_type: str
    parent_client_order_id: str
    quantity: str
    side: str
    status: str
    symbol: str
    time_in_force: str
    updated_at: str
    venue: str


@dataclass(frozen=True)
class GatewayInput:
    schema_version: str
    version: str
    status: str
    decision: str
    route_sha256: str
    accepted_count: int
    rejected_count: int
    duplicate_count: int
    orders: list[dict[str, Any]]
    ledger: list[dict[str, Any]]
    rejection_reasons: list[str]
    network_used: bool
    gateway_sha256: str


@dataclass(frozen=True)
class FillEvent:
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
class FillLedgerEntry:
    sequence: int
    event_type: str
    broker_order_id: str
    fill_id: str | None
    prior_status: str
    new_status: str
    event_at: str
    previous_entry_sha256: str
    payload_sha256: str
    entry_sha256: str


@dataclass(frozen=True)
class OrderFillResult:
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
class FillSimulationResult:
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


class PaperFillSimulator:
    def __init__(
        self,
        *,
        mode: str = "paper",
        enable_live: bool = False,
        reference_time: str | None = None,
        slippage_bps: str = "2.0",
        commission_per_share: str = "0.005",
        minimum_commission: str = "1.00",
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
        self.slippage_bps = d(slippage_bps, field="slippage_bps")
        self.commission_per_share = d(
            commission_per_share, field="commission_per_share"
        )
        self.minimum_commission = d(
            minimum_commission, field="minimum_commission"
        )
        if self.slippage_bps < 0:
            raise ValueError("slippage_bps must be non-negative")
        if self.commission_per_share < 0:
            raise ValueError("commission_per_share must be non-negative")
        if self.minimum_commission < 0:
            raise ValueError("minimum_commission must be non-negative")
        self.ledger: list[FillLedgerEntry] = []

    def _live_gate(self) -> None:
        if self.mode == "live":
            if not self.enable_live:
                raise PermissionError("live mode requires --enable-live")
            raise NotImplementedError(
                "live broker transport is intentionally not implemented in V48.0"
            )

    @staticmethod
    def _gateway_hash_payload(gateway: GatewayInput) -> dict[str, Any]:
        return {
            "schema_version": gateway.schema_version,
            "version": gateway.version,
            "status": gateway.status,
            "decision": gateway.decision,
            "route_sha256": gateway.route_sha256,
            "accepted_count": gateway.accepted_count,
            "rejected_count": gateway.rejected_count,
            "duplicate_count": gateway.duplicate_count,
            "orders": gateway.orders,
            "ledger": gateway.ledger,
            "rejection_reasons": gateway.rejection_reasons,
            "network_used": gateway.network_used,
        }

    @staticmethod
    def _order_hash_payload(order: BrokerOrderInput) -> dict[str, Any]:
        return {
            "broker_order_id": order.broker_order_id,
            "child_order_id": order.child_order_id,
            "parent_client_order_id": order.parent_client_order_id,
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "order_type": order.order_type,
            "time_in_force": order.time_in_force,
            "limit_price": order.limit_price,
            "venue": order.venue,
            "status": order.status,
            "accepted_at": order.accepted_at,
            "updated_at": order.updated_at,
            "network_used": order.network_used,
        }

    def _event_time(self, offset: int) -> str:
        dt = self.reference_time + timedelta(microseconds=offset)
        return dt.isoformat().replace("+00:00", "Z")

    def _append_ledger(
        self,
        *,
        event_type: str,
        broker_order_id: str,
        fill_id: str | None,
        prior_status: str,
        new_status: str,
        event_at: str,
    ) -> None:
        previous = self.ledger[-1].entry_sha256 if self.ledger else "GENESIS"
        payload = {
            "event_type": event_type,
            "broker_order_id": broker_order_id,
            "fill_id": fill_id,
            "prior_status": prior_status,
            "new_status": new_status,
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
            FillLedgerEntry(**core, entry_sha256=canonical_hash(core))
        )

    def _effective_price(
        self,
        *,
        order: BrokerOrderInput,
        reference_price: Decimal,
    ) -> Decimal | None:
        side = order.side.lower()
        order_type = order.order_type.lower()
        limit_price = (
            d(order.limit_price, field="limit_price")
            if order.limit_price is not None
            else None
        )

        if order_type == "limit":
            if limit_price is None or limit_price <= 0:
                raise ValueError(
                    f"limit order requires positive limit_price: {order.broker_order_id}"
                )
            if side == "buy" and reference_price > limit_price:
                return None
            if side == "sell" and reference_price < limit_price:
                return None
        elif order_type != "market":
            raise ValueError(
                f"order_type must be market or limit: {order.broker_order_id}"
            )

        multiplier = Decimal("1") + (
            self.slippage_bps / Decimal("10000")
            if side == "buy"
            else -self.slippage_bps / Decimal("10000")
        )
        execution = reference_price * multiplier

        if order_type == "limit" and limit_price is not None:
            if side == "buy":
                execution = min(execution, limit_price)
            else:
                execution = max(execution, limit_price)

        if execution <= 0:
            raise ValueError("calculated execution price must be positive")
        return execution

    def _commission(self, quantity: Decimal) -> Decimal:
        if quantity <= 0:
            return Decimal("0")
        return max(
            quantity * self.commission_per_share,
            self.minimum_commission,
        )

    def _simulate_order(
        self,
        *,
        order: BrokerOrderInput,
        reference_price: Decimal,
        liquidity_slices: list[Decimal],
        event_offset: int,
    ) -> OrderFillResult:
        requested = d(order.quantity, field="quantity")
        if requested <= 0:
            raise ValueError(
                f"quantity must be positive: {order.broker_order_id}"
            )
        if order.status != "ACCEPTED":
            raise ValueError(
                f"order status must be ACCEPTED: {order.broker_order_id}"
            )
        if order.network_used is not False:
            raise ValueError(
                f"order reports network_used=true: {order.broker_order_id}"
            )
        expected_hash = canonical_hash(self._order_hash_payload(order))
        if expected_hash != order.broker_order_sha256:
            raise ValueError(
                f"broker order SHA-256 verification failed: {order.broker_order_id}"
            )

        execution_price = self._effective_price(
            order=order,
            reference_price=reference_price,
        )

        fills: list[FillEvent] = []
        filled = Decimal("0")
        gross = Decimal("0")
        commission_total = Decimal("0")
        current_status = "ACCEPTED"

        if execution_price is not None:
            self._append_ledger(
                event_type="ORDER_WORKING",
                broker_order_id=order.broker_order_id,
                fill_id=None,
                prior_status=current_status,
                new_status="WORKING",
                event_at=self._event_time(event_offset),
            )
            current_status = "WORKING"

            for index, available in enumerate(liquidity_slices, start=1):
                if filled >= requested:
                    break
                if available <= 0:
                    continue
                fill_qty = min(available, requested - filled)
                fill_price = execution_price
                fill_gross = fill_qty * fill_price
                fill_commission = self._commission(fill_qty)
                fill_time = self._event_time(
                    event_offset + len(self.ledger) + index
                )
                fill_identity = {
                    "version": VERSION,
                    "broker_order_id": order.broker_order_id,
                    "sequence": index,
                    "fill_quantity": q_qty(fill_qty),
                    "fill_price": q_money(fill_price),
                    "event_at": fill_time,
                }
                fill_id = "fill-" + canonical_hash(fill_identity)[:24]
                core = {
                    "fill_id": fill_id,
                    "broker_order_id": order.broker_order_id,
                    "symbol": order.symbol.upper(),
                    "side": order.side.lower(),
                    "fill_quantity": q_qty(fill_qty),
                    "fill_price": q_money(fill_price),
                    "gross_notional": q_money(fill_gross),
                    "commission": q_money(fill_commission),
                    "slippage_bps": q_money(self.slippage_bps),
                    "reference_price": q_money(reference_price),
                    "event_at": fill_time,
                    "network_used": False,
                }
                fill = FillEvent(
                    **core,
                    fill_sha256=canonical_hash(core),
                )
                fills.append(fill)
                filled += fill_qty
                gross += fill_gross
                commission_total += fill_commission

                new_status = (
                    "FILLED" if filled >= requested else "PARTIAL_FILL"
                )
                self._append_ledger(
                    event_type=(
                        "ORDER_FILLED"
                        if new_status == "FILLED"
                        else "ORDER_PARTIAL_FILL"
                    ),
                    broker_order_id=order.broker_order_id,
                    fill_id=fill_id,
                    prior_status=current_status,
                    new_status=new_status,
                    event_at=fill_time,
                )
                current_status = new_status

        remaining = requested - filled
        if filled == 0:
            final_status = "WORKING" if execution_price is not None else "ACCEPTED"
            average = None
        elif remaining > 0:
            final_status = "PARTIAL_FILL"
            average = gross / filled
        else:
            final_status = "FILLED"
            average = gross / filled

        core = {
            "broker_order_id": order.broker_order_id,
            "child_order_id": order.child_order_id,
            "symbol": order.symbol.upper(),
            "side": order.side.lower(),
            "requested_quantity": q_qty(requested),
            "filled_quantity": q_qty(filled),
            "remaining_quantity": q_qty(remaining),
            "weighted_average_fill_price": (
                q_money(average) if average is not None else None
            ),
            "gross_notional": q_money(gross),
            "total_commission": q_money(commission_total),
            "final_status": final_status,
            "fills": [asdict(fill) for fill in fills],
        }
        return OrderFillResult(
            **core,
            order_result_sha256=canonical_hash(core),
        )

    def simulate(
        self,
        gateway: GatewayInput,
        *,
        reference_price: str,
        liquidity_slices: list[str],
    ) -> FillSimulationResult:
        self._live_gate()
        reasons: list[str] = []
        expected_gateway_hash = canonical_hash(
            self._gateway_hash_payload(gateway)
        )
        if gateway.status != "PASS":
            reasons.append("V47 gateway status must be PASS.")
        if gateway.decision != "accept":
            reasons.append("V47 gateway decision must be accept.")
        if gateway.network_used is not False:
            reasons.append("V47 gateway must report network_used=false.")
        if gateway.rejection_reasons:
            reasons.append("V47 gateway contains rejection reasons.")
        if gateway.accepted_count != len(gateway.orders):
            reasons.append("V47 accepted_count does not match orders length.")
        if expected_gateway_hash != gateway.gateway_sha256:
            reasons.append("V47 gateway SHA-256 verification failed.")

        ref_price = d(reference_price, field="reference_price")
        if ref_price <= 0:
            reasons.append("reference_price must be positive.")

        slices: list[Decimal] = []
        for value in liquidity_slices:
            parsed = d(value, field="liquidity_slice")
            if parsed < 0:
                reasons.append("liquidity slices must be non-negative.")
                break
            slices.append(parsed)

        order_results: list[OrderFillResult] = []
        if not reasons:
            for index, raw in enumerate(gateway.orders, start=1):
                try:
                    order = BrokerOrderInput(**raw)
                    order_results.append(
                        self._simulate_order(
                            order=order,
                            reference_price=ref_price,
                            liquidity_slices=slices,
                            event_offset=index * 100,
                        )
                    )
                except (TypeError, ValueError) as exc:
                    reasons.append(str(exc))

        fully = sum(x.final_status == "FILLED" for x in order_results)
        partial = sum(x.final_status == "PARTIAL_FILL" for x in order_results)
        unfilled = sum(
            x.final_status in {"ACCEPTED", "WORKING"}
            for x in order_results
        )
        total_qty = sum(
            (
                d(x.filled_quantity, field="filled_quantity")
                for x in order_results
            ),
            Decimal("0"),
        )
        total_gross = sum(
            (
                d(x.gross_notional, field="gross_notional")
                for x in order_results
            ),
            Decimal("0"),
        )
        total_commission = sum(
            (
                d(x.total_commission, field="total_commission")
                for x in order_results
            ),
            Decimal("0"),
        )

        status = "PASS" if not reasons else "FAIL"
        decision = "simulate" if not reasons else "reject"
        core = {
            "schema_version": "v48.0.paper_fill_simulation.1",
            "version": VERSION,
            "status": status,
            "decision": decision,
            "gateway_sha256": gateway.gateway_sha256,
            "order_count": len(order_results),
            "fill_event_count": sum(len(x.fills) for x in order_results),
            "fully_filled_count": fully,
            "partially_filled_count": partial,
            "unfilled_count": unfilled,
            "total_filled_quantity": q_qty(total_qty),
            "total_gross_notional": q_money(total_gross),
            "total_commission": q_money(total_commission),
            "orders": [asdict(x) for x in order_results],
            "ledger": [asdict(x) for x in self.ledger],
            "rejection_reasons": reasons,
            "network_used": False,
        }
        return FillSimulationResult(
            **core,
            simulation_sha256=canonical_hash(core),
        )

    @staticmethod
    def export(path: Path, result: FillSimulationResult) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "v48.0.paper_fill_simulation_export.1",
            "version": VERSION,
            "result": asdict(result),
            "network_used": False,
        }
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def load_gateway(path: Path) -> GatewayInput:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("result", payload)
    return GatewayInput(**raw)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="V48.0 Paper Fill Simulator Foundation"
    )
    parser.add_argument(
        "--input",
        default="release/v47/audit/paper_broker_gateway_result_v47_0.json",
    )
    parser.add_argument("--mode", choices=["replay", "paper", "live"], default="paper")
    parser.add_argument("--enable-live", action="store_true")
    parser.add_argument("--reference-time")
    parser.add_argument("--reference-price", required=True)
    parser.add_argument(
        "--liquidity-slices",
        default="1000000",
        help="Comma-separated available quantities, e.g. 20,20,100",
    )
    parser.add_argument("--slippage-bps", default="2.0")
    parser.add_argument("--commission-per-share", default="0.005")
    parser.add_argument("--minimum-commission", default="1.00")
    parser.add_argument(
        "--output",
        default="release/v48/audit/paper_fill_simulation_result_v48_0.json",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output)
    try:
        simulator = PaperFillSimulator(
            mode=args.mode,
            enable_live=args.enable_live,
            reference_time=args.reference_time,
            slippage_bps=args.slippage_bps,
            commission_per_share=args.commission_per_share,
            minimum_commission=args.minimum_commission,
        )
        gateway = load_gateway(Path(args.input))
        slices = [
            item.strip()
            for item in args.liquidity_slices.split(",")
            if item.strip()
        ]
        result = simulator.simulate(
            gateway,
            reference_price=args.reference_price,
            liquidity_slices=slices,
        )
        simulator.export(output, result)
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
            "schema_version": "v48.0.paper_fill_simulation_error.1",
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
