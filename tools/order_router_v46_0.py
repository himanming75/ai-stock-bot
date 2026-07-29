#!/usr/bin/env python3
"""
V46.0 Order Router Foundation

Consumes a V45 risk-policy decision and creates a deterministic offline
paper-routing plan. This version does not connect to a broker, exchange,
market-data service, or network transport.

Main protections:
- verifies V45 status, decision, integrity hash, and network_used=false
- blocks rejected or malformed risk decisions
- enforces live-mode safety gate
- validates symbol, side, quantity, order type, TIF, and prices
- limits total route quantity and child-order quantity
- supports deterministic single-route or split-route plans
- generates child-order and route-plan SHA-256 hashes
- exports an auditable JSON result
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Sequence

VERSION = "46.0"


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def to_decimal(value: Any, name: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not number.is_finite():
        raise ValueError(f"{name} must be finite")
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
class RiskDecisionInput:
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


@dataclass(frozen=True)
class RouterConfig:
    primary_venue: str = "PAPER_PRIMARY"
    secondary_venue: str = "PAPER_SECONDARY"
    max_total_quantity: str = "10000"
    max_child_quantity: str = "500"
    split_threshold_quantity: str = "100"
    primary_allocation_pct: str = "60"
    lot_size: str = "1"
    allow_odd_lot: bool = False

    def validate(self) -> None:
        if not self.primary_venue.strip():
            raise ValueError("primary_venue is required")
        if not self.secondary_venue.strip():
            raise ValueError("secondary_venue is required")
        if self.primary_venue.strip().upper() == self.secondary_venue.strip().upper():
            raise ValueError("primary_venue and secondary_venue must be different")
        positive(self.max_total_quantity, "max_total_quantity")
        positive(self.max_child_quantity, "max_child_quantity")
        positive(self.split_threshold_quantity, "split_threshold_quantity")
        lot = positive(self.lot_size, "lot_size")
        pct = positive(self.primary_allocation_pct, "primary_allocation_pct")
        if pct >= 100:
            raise ValueError("primary_allocation_pct must be less than 100")
        if lot != lot.to_integral_value():
            raise ValueError("lot_size must be a whole number")


@dataclass(frozen=True)
class RouteRequest:
    quantity: str
    order_type: str = "market"
    time_in_force: str = "day"
    limit_price: str | None = None


@dataclass(frozen=True)
class ChildOrder:
    sequence: int
    child_order_id: str
    parent_client_order_id: str
    symbol: str
    side: str
    quantity: str
    order_type: str
    time_in_force: str
    limit_price: str | None
    venue: str
    status: str
    network_used: bool
    child_sha256: str


@dataclass(frozen=True)
class RoutePlan:
    schema_version: str
    version: str
    status: str
    route_decision: str
    parent_client_order_id: str | None
    symbol: str
    side: str | None
    requested_quantity: str
    routed_quantity: str
    child_order_count: int
    order_type: str
    time_in_force: str
    limit_price: str | None
    checks: list[dict[str, Any]]
    rejection_reasons: list[str]
    children: list[dict[str, Any]]
    network_used: bool
    route_sha256: str


class OrderRouter:
    def __init__(
        self,
        config: RouterConfig | None = None,
        *,
        mode: str = "paper",
        enable_live: bool = False,
    ) -> None:
        self.config = config or RouterConfig()
        self.config.validate()
        if mode not in {"replay", "paper", "live"}:
            raise ValueError("mode must be replay, paper, or live")
        self.mode = mode
        self.enable_live = enable_live

    def _live_gate(self) -> None:
        if self.mode == "live":
            if not self.enable_live:
                raise PermissionError("live mode requires --enable-live")
            raise NotImplementedError(
                "live broker transport is intentionally not implemented in V46.0"
            )

    @staticmethod
    def _risk_hash_payload(risk: RiskDecisionInput) -> dict[str, Any]:
        return {
            "schema_version": risk.schema_version,
            "version": risk.version,
            "status": risk.status,
            "decision": risk.decision,
            "symbol": risk.symbol,
            "client_order_id": risk.client_order_id,
            "side": risk.side,
            "order_notional": risk.order_notional,
            "estimated_risk_amount": risk.estimated_risk_amount,
            "estimated_risk_pct": risk.estimated_risk_pct,
            "projected_position_weight_pct": risk.projected_position_weight_pct,
            "projected_symbol_exposure_pct": risk.projected_symbol_exposure_pct,
            "projected_gross_exposure_pct": risk.projected_gross_exposure_pct,
            "projected_cash_reserve_pct": risk.projected_cash_reserve_pct,
            "checks": risk.checks,
            "rejection_reasons": risk.rejection_reasons,
            "network_used": risk.network_used,
        }

    @staticmethod
    def _child_core(
        *,
        sequence: int,
        parent_client_order_id: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        order_type: str,
        time_in_force: str,
        limit_price: str | None,
        venue: str,
    ) -> dict[str, Any]:
        identity = {
            "sequence": sequence,
            "parent_client_order_id": parent_client_order_id,
            "symbol": symbol,
            "side": side,
            "quantity": normalize(quantity),
            "order_type": order_type,
            "time_in_force": time_in_force,
            "limit_price": limit_price,
            "venue": venue,
        }
        child_order_id = "v46-" + canonical_hash(identity)[:24]
        return {
            **identity,
            "child_order_id": child_order_id,
            "status": "ROUTED_PAPER",
            "network_used": False,
        }

    @staticmethod
    def _make_child(**kwargs: Any) -> ChildOrder:
        core = OrderRouter._child_core(**kwargs)
        return ChildOrder(**core, child_sha256=canonical_hash(core))

    def _split_allocations(self, quantity: Decimal) -> list[tuple[str, Decimal]]:
        threshold = positive(
            self.config.split_threshold_quantity, "split_threshold_quantity"
        )
        max_child = positive(self.config.max_child_quantity, "max_child_quantity")
        lot = positive(self.config.lot_size, "lot_size")
        primary_pct = positive(
            self.config.primary_allocation_pct, "primary_allocation_pct"
        )

        if quantity < threshold:
            targets = [(self.config.primary_venue.strip().upper(), quantity)]
        else:
            primary_qty = (quantity * primary_pct / Decimal("100"))
            primary_qty = (primary_qty // lot) * lot
            secondary_qty = quantity - primary_qty
            if primary_qty == 0:
                primary_qty = min(lot, quantity)
                secondary_qty = quantity - primary_qty
            targets = [
                (self.config.primary_venue.strip().upper(), primary_qty),
                (self.config.secondary_venue.strip().upper(), secondary_qty),
            ]

        allocations: list[tuple[str, Decimal]] = []
        for venue, target in targets:
            remaining = target
            while remaining > 0:
                child_qty = min(max_child, remaining)
                if not self.config.allow_odd_lot and child_qty % lot != 0:
                    child_qty = (child_qty // lot) * lot
                if child_qty <= 0:
                    raise ValueError(
                        "routing produced a zero child quantity; check lot and child limits"
                    )
                allocations.append((venue, child_qty))
                remaining -= child_qty
        return allocations

    def route(self, risk: RiskDecisionInput, request: RouteRequest) -> RoutePlan:
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

        expected_hash = canonical_hash(self._risk_hash_payload(risk))
        record(
            "risk.status",
            risk.status == "PASS",
            "V45 risk-policy status must be PASS.",
        )
        record(
            "risk.decision",
            risk.decision.lower() == "approve",
            "V45 risk-policy decision must be approve.",
        )
        record(
            "risk.hash",
            expected_hash == risk.decision_sha256,
            "V45 risk-policy SHA-256 verification failed.",
        )
        record(
            "risk.network",
            risk.network_used is False,
            "V45 risk-policy result must report network_used=false.",
        )
        record(
            "risk.rejections",
            len(risk.rejection_reasons) == 0,
            "V45 risk-policy result contains rejection reasons.",
        )

        symbol = risk.symbol.strip().upper()
        side = risk.side.lower() if risk.side else None
        record("order.symbol", bool(symbol), "Symbol is required.")
        record("order.side", side in {"buy", "sell"}, "Side must be buy or sell.")
        record(
            "order.client_order_id",
            bool(risk.client_order_id),
            "client_order_id is required.",
        )

        quantity = positive(request.quantity, "quantity")
        max_total = positive(self.config.max_total_quantity, "max_total_quantity")
        record(
            "quantity.maximum",
            quantity <= max_total,
            f"Quantity exceeds router maximum {normalize(max_total)}.",
        )

        lot = positive(self.config.lot_size, "lot_size")
        lot_ok = self.config.allow_odd_lot or quantity % lot == 0
        record(
            "quantity.lot_size",
            lot_ok,
            f"Quantity must be a multiple of lot size {normalize(lot)}.",
        )

        order_type = request.order_type.strip().lower()
        tif = request.time_in_force.strip().lower()
        record(
            "order.type",
            order_type in {"market", "limit"},
            "Order type must be market or limit.",
        )
        record(
            "order.time_in_force",
            tif in {"day", "gtc"},
            "Time in force must be day or gtc.",
        )

        limit_price: str | None = None
        if order_type == "limit":
            try:
                limit_price = normalize(positive(request.limit_price, "limit_price"))
                record("order.limit_price", True, "Limit price is valid.")
            except ValueError as exc:
                record("order.limit_price", False, str(exc))
        elif request.limit_price is not None:
            record(
                "order.market_price",
                False,
                "Market orders must not include a limit price.",
            )
        else:
            record(
                "order.market_price",
                True,
                "Market order does not include a limit price.",
            )

        children: list[ChildOrder] = []
        if not reasons:
            allocations = self._split_allocations(quantity)
            parent_id = str(risk.client_order_id)
            for sequence, (venue, child_qty) in enumerate(allocations, start=1):
                children.append(
                    self._make_child(
                        sequence=sequence,
                        parent_client_order_id=parent_id,
                        symbol=symbol,
                        side=str(side),
                        quantity=child_qty,
                        order_type=order_type,
                        time_in_force=tif,
                        limit_price=limit_price,
                        venue=venue,
                    )
                )

        routed_quantity = sum(
            (to_decimal(child.quantity, "child quantity") for child in children),
            Decimal("0"),
        )
        route_decision = "route" if not reasons else "reject"
        status = "PASS" if route_decision == "route" else "FAIL"

        core = {
            "schema_version": "v46.0.route_plan.1",
            "version": VERSION,
            "status": status,
            "route_decision": route_decision,
            "parent_client_order_id": risk.client_order_id,
            "symbol": symbol,
            "side": side,
            "requested_quantity": normalize(quantity),
            "routed_quantity": normalize(routed_quantity),
            "child_order_count": len(children),
            "order_type": order_type,
            "time_in_force": tif,
            "limit_price": limit_price,
            "checks": checks,
            "rejection_reasons": reasons,
            "children": [asdict(child) for child in children],
            "network_used": False,
        }
        return RoutePlan(**core, route_sha256=canonical_hash(core))

    @staticmethod
    def export(path: Path, plan: RoutePlan) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "v46.0.order_router_export.1",
            "version": VERSION,
            "result": asdict(plan),
            "network_used": False,
        }
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def load_risk_decision(path: Path) -> RiskDecisionInput:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("decision", payload.get("result", payload))
    return RiskDecisionInput(**raw)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="V46.0 Order Router Foundation"
    )
    parser.add_argument(
        "--input",
        default="release/v45/audit/risk_policy_result_v45_0.json",
    )
    parser.add_argument("--quantity", required=True)
    parser.add_argument("--order-type", choices=["market", "limit"], default="market")
    parser.add_argument("--time-in-force", choices=["day", "gtc"], default="day")
    parser.add_argument("--limit-price")
    parser.add_argument("--primary-venue", default="PAPER_PRIMARY")
    parser.add_argument("--secondary-venue", default="PAPER_SECONDARY")
    parser.add_argument("--max-total-quantity", default="10000")
    parser.add_argument("--max-child-quantity", default="500")
    parser.add_argument("--split-threshold-quantity", default="100")
    parser.add_argument("--primary-allocation-pct", default="60")
    parser.add_argument("--lot-size", default="1")
    parser.add_argument("--allow-odd-lot", action="store_true")
    parser.add_argument("--mode", choices=["replay", "paper", "live"], default="paper")
    parser.add_argument("--enable-live", action="store_true")
    parser.add_argument(
        "--output",
        default="release/v46/audit/order_route_result_v46_0.json",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        router = OrderRouter(
            RouterConfig(
                primary_venue=args.primary_venue,
                secondary_venue=args.secondary_venue,
                max_total_quantity=args.max_total_quantity,
                max_child_quantity=args.max_child_quantity,
                split_threshold_quantity=args.split_threshold_quantity,
                primary_allocation_pct=args.primary_allocation_pct,
                lot_size=args.lot_size,
                allow_odd_lot=args.allow_odd_lot,
            ),
            mode=args.mode,
            enable_live=args.enable_live,
        )
        risk = load_risk_decision(Path(args.input))
        plan = router.route(
            risk,
            RouteRequest(
                quantity=args.quantity,
                order_type=args.order_type,
                time_in_force=args.time_in_force,
                limit_price=args.limit_price,
            ),
        )
        router.export(Path(args.output), plan)
        print(json.dumps(asdict(plan), indent=2, sort_keys=True))
        return 0 if plan.status == "PASS" else 1
    except (
        TypeError,
        ValueError,
        PermissionError,
        NotImplementedError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        error = {
            "schema_version": "v46.0.order_router_error.1",
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
