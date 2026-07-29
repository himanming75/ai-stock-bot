#!/usr/bin/env python3
"""
V47.0 Paper Broker Gateway Foundation

Consumes a V46 paper route plan and accepts child orders into an offline,
deterministic paper-broker ledger.

No real broker connection, network transport, market-data request, or live
order submission is implemented.

Features:
- V46 route-plan status, decision, integrity, and network checks
- deterministic broker order IDs
- duplicate child-order detection
- accepted/working/cancelled lifecycle controls
- cancellation eligibility checks
- append-only in-memory ledger with hash chaining
- deterministic export for audit and replay
- explicit live-mode safety gate
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

VERSION = "47.0"


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


@dataclass(frozen=True)
class ChildOrderInput:
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
class RoutePlanInput:
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


@dataclass(frozen=True)
class BrokerOrder:
    broker_order_id: str
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
    accepted_at: str
    updated_at: str
    network_used: bool
    broker_order_sha256: str


@dataclass(frozen=True)
class LedgerEntry:
    sequence: int
    event_type: str
    broker_order_id: str
    child_order_id: str
    prior_status: str | None
    new_status: str
    event_at: str
    previous_entry_sha256: str
    payload_sha256: str
    entry_sha256: str


@dataclass(frozen=True)
class GatewayResult:
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


class PaperBrokerGateway:
    TERMINAL_STATUSES = {"FILLED", "CANCELLED", "REJECTED"}
    CANCELLABLE_STATUSES = {"ACCEPTED", "WORKING", "PARTIAL_FILL"}

    def __init__(
        self,
        *,
        mode: str = "paper",
        enable_live: bool = False,
        reference_time: str | None = None,
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
        self.orders: dict[str, BrokerOrder] = {}
        self.child_index: dict[str, str] = {}
        self.ledger: list[LedgerEntry] = []

    def _live_gate(self) -> None:
        if self.mode == "live":
            if not self.enable_live:
                raise PermissionError("live mode requires --enable-live")
            raise NotImplementedError(
                "live broker transport is intentionally not implemented in V47.0"
            )

    @staticmethod
    def _route_hash_payload(route: RoutePlanInput) -> dict[str, Any]:
        return {
            "schema_version": route.schema_version,
            "version": route.version,
            "status": route.status,
            "route_decision": route.route_decision,
            "parent_client_order_id": route.parent_client_order_id,
            "symbol": route.symbol,
            "side": route.side,
            "requested_quantity": route.requested_quantity,
            "routed_quantity": route.routed_quantity,
            "child_order_count": route.child_order_count,
            "order_type": route.order_type,
            "time_in_force": route.time_in_force,
            "limit_price": route.limit_price,
            "checks": route.checks,
            "rejection_reasons": route.rejection_reasons,
            "children": route.children,
            "network_used": route.network_used,
        }

    @staticmethod
    def _child_hash_payload(child: ChildOrderInput) -> dict[str, Any]:
        return {
            "sequence": child.sequence,
            "child_order_id": child.child_order_id,
            "parent_client_order_id": child.parent_client_order_id,
            "symbol": child.symbol,
            "side": child.side,
            "quantity": child.quantity,
            "order_type": child.order_type,
            "time_in_force": child.time_in_force,
            "limit_price": child.limit_price,
            "venue": child.venue,
            "status": child.status,
            "network_used": child.network_used,
        }

    def _event_time(self, offset: int = 0) -> str:
        if offset == 0:
            dt = self.reference_time
        else:
            from datetime import timedelta
            dt = self.reference_time + timedelta(microseconds=offset)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _broker_order_core(
        *,
        broker_order_id: str,
        child: ChildOrderInput,
        status: str,
        accepted_at: str,
        updated_at: str,
    ) -> dict[str, Any]:
        return {
            "broker_order_id": broker_order_id,
            "child_order_id": child.child_order_id,
            "parent_client_order_id": child.parent_client_order_id,
            "symbol": child.symbol.strip().upper(),
            "side": child.side.lower(),
            "quantity": child.quantity,
            "order_type": child.order_type.lower(),
            "time_in_force": child.time_in_force.lower(),
            "limit_price": child.limit_price,
            "venue": child.venue.strip().upper(),
            "status": status,
            "accepted_at": accepted_at,
            "updated_at": updated_at,
            "network_used": False,
        }

    def _append_ledger(
        self,
        *,
        event_type: str,
        order: BrokerOrder,
        prior_status: str | None,
        new_status: str,
        event_at: str,
    ) -> LedgerEntry:
        previous_hash = self.ledger[-1].entry_sha256 if self.ledger else "GENESIS"
        payload = {
            "event_type": event_type,
            "broker_order_id": order.broker_order_id,
            "child_order_id": order.child_order_id,
            "prior_status": prior_status,
            "new_status": new_status,
            "event_at": event_at,
        }
        payload_hash = canonical_hash(payload)
        core = {
            "sequence": len(self.ledger) + 1,
            **payload,
            "previous_entry_sha256": previous_hash,
            "payload_sha256": payload_hash,
        }
        entry = LedgerEntry(**core, entry_sha256=canonical_hash(core))
        self.ledger.append(entry)
        return entry

    def _accept_child(
        self,
        child: ChildOrderInput,
        *,
        event_offset: int,
    ) -> tuple[BrokerOrder | None, str | None]:
        if child.child_order_id in self.child_index:
            return None, f"Duplicate child order: {child.child_order_id}"

        expected_child_hash = canonical_hash(self._child_hash_payload(child))
        if expected_child_hash != child.child_sha256:
            return None, f"Child SHA-256 verification failed: {child.child_order_id}"
        if child.network_used is not False:
            return None, f"Child order reports network_used=true: {child.child_order_id}"
        if child.status != "ROUTED_PAPER":
            return None, f"Child order status must be ROUTED_PAPER: {child.child_order_id}"
        if not child.child_order_id.strip():
            return None, "child_order_id is required"
        if not child.parent_client_order_id.strip():
            return None, f"parent_client_order_id is required: {child.child_order_id}"
        if not child.symbol.strip():
            return None, f"symbol is required: {child.child_order_id}"
        if child.side.lower() not in {"buy", "sell"}:
            return None, f"side must be buy or sell: {child.child_order_id}"

        broker_identity = {
            "version": VERSION,
            "child_order_id": child.child_order_id,
            "parent_client_order_id": child.parent_client_order_id,
            "venue": child.venue.strip().upper(),
        }
        broker_order_id = "paper-" + canonical_hash(broker_identity)[:24]
        accepted_at = self._event_time(event_offset)
        core = self._broker_order_core(
            broker_order_id=broker_order_id,
            child=child,
            status="ACCEPTED",
            accepted_at=accepted_at,
            updated_at=accepted_at,
        )
        order = BrokerOrder(
            **core,
            broker_order_sha256=canonical_hash(core),
        )
        self.orders[broker_order_id] = order
        self.child_index[child.child_order_id] = broker_order_id
        self._append_ledger(
            event_type="ORDER_ACCEPTED",
            order=order,
            prior_status=None,
            new_status="ACCEPTED",
            event_at=accepted_at,
        )
        return order, None

    def accept_route(self, route: RoutePlanInput) -> GatewayResult:
        self._live_gate()

        reasons: list[str] = []
        expected_route_hash = canonical_hash(self._route_hash_payload(route))

        if route.status != "PASS":
            reasons.append("V46 route-plan status must be PASS.")
        if route.route_decision != "route":
            reasons.append("V46 route-plan decision must be route.")
        if expected_route_hash != route.route_sha256:
            reasons.append("V46 route-plan SHA-256 verification failed.")
        if route.network_used is not False:
            reasons.append("V46 route-plan must report network_used=false.")
        if route.rejection_reasons:
            reasons.append("V46 route-plan contains rejection reasons.")
        if route.child_order_count != len(route.children):
            reasons.append("V46 child_order_count does not match children length.")

        accepted: list[BrokerOrder] = []
        duplicate_count = 0

        if not reasons:
            for index, raw in enumerate(route.children, start=1):
                try:
                    child = ChildOrderInput(**raw)
                except TypeError as exc:
                    reasons.append(f"Invalid child order at index {index}: {exc}")
                    continue

                order, error = self._accept_child(child, event_offset=index)
                if error:
                    reasons.append(error)
                    if error.startswith("Duplicate child order:"):
                        duplicate_count += 1
                elif order is not None:
                    accepted.append(order)

        rejected_count = len(route.children) - len(accepted)
        decision = "accept" if not reasons else "reject"
        status = "PASS" if not reasons else "FAIL"

        core = {
            "schema_version": "v47.0.paper_broker_gateway.1",
            "version": VERSION,
            "status": status,
            "decision": decision,
            "route_sha256": route.route_sha256,
            "accepted_count": len(accepted),
            "rejected_count": rejected_count,
            "duplicate_count": duplicate_count,
            "orders": [asdict(order) for order in accepted],
            "ledger": [asdict(entry) for entry in self.ledger],
            "rejection_reasons": reasons,
            "network_used": False,
        }
        return GatewayResult(**core, gateway_sha256=canonical_hash(core))

    def transition_order(
        self,
        broker_order_id: str,
        new_status: str,
        *,
        event_type: str | None = None,
    ) -> BrokerOrder:
        self._live_gate()
        if broker_order_id not in self.orders:
            raise KeyError(f"unknown broker_order_id: {broker_order_id}")

        current = self.orders[broker_order_id]
        new_status = new_status.strip().upper()
        allowed = {
            "ACCEPTED": {"WORKING", "CANCELLED", "REJECTED"},
            "WORKING": {"PARTIAL_FILL", "FILLED", "CANCELLED", "REJECTED"},
            "PARTIAL_FILL": {"WORKING", "FILLED", "CANCELLED", "REJECTED"},
            "FILLED": set(),
            "CANCELLED": set(),
            "REJECTED": set(),
        }
        if new_status not in allowed.get(current.status, set()):
            raise ValueError(
                f"invalid transition {current.status} -> {new_status}"
            )

        updated_at = self._event_time(len(self.ledger) + 1)
        core = {
            **asdict(current),
            "status": new_status,
            "updated_at": updated_at,
        }
        core.pop("broker_order_sha256")
        updated = BrokerOrder(
            **core,
            broker_order_sha256=canonical_hash(core),
        )
        self.orders[broker_order_id] = updated
        self._append_ledger(
            event_type=event_type or f"ORDER_{new_status}",
            order=updated,
            prior_status=current.status,
            new_status=new_status,
            event_at=updated_at,
        )
        return updated

    def cancel_order(self, broker_order_id: str) -> BrokerOrder:
        if broker_order_id not in self.orders:
            raise KeyError(f"unknown broker_order_id: {broker_order_id}")
        current = self.orders[broker_order_id]
        if current.status not in self.CANCELLABLE_STATUSES:
            raise ValueError(f"order in {current.status} status cannot be cancelled")
        return self.transition_order(
            broker_order_id,
            "CANCELLED",
            event_type="ORDER_CANCELLED",
        )

    @staticmethod
    def export(path: Path, result: GatewayResult) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "v47.0.paper_broker_gateway_export.1",
            "version": VERSION,
            "result": asdict(result),
            "network_used": False,
        }
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def load_route(path: Path) -> RoutePlanInput:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("result", payload)
    return RoutePlanInput(**raw)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="V47.0 Paper Broker Gateway Foundation"
    )
    parser.add_argument(
        "--input",
        default="release/v46/audit/order_route_result_v46_0.json",
    )
    parser.add_argument("--mode", choices=["replay", "paper", "live"], default="paper")
    parser.add_argument("--enable-live", action="store_true")
    parser.add_argument("--reference-time")
    parser.add_argument(
        "--output",
        default="release/v47/audit/paper_broker_gateway_result_v47_0.json",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        gateway = PaperBrokerGateway(
            mode=args.mode,
            enable_live=args.enable_live,
            reference_time=args.reference_time,
        )
        route = load_route(Path(args.input))
        result = gateway.accept_route(route)
        gateway.export(Path(args.output), result)
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
        return 0 if result.status == "PASS" else 1
    except (
        TypeError,
        ValueError,
        PermissionError,
        NotImplementedError,
        KeyError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        error = {
            "schema_version": "v47.0.paper_broker_gateway_error.1",
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
