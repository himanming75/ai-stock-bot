#!/usr/bin/env python3
"""
V57.0 Trade Execution Coordinator Foundation

Deterministic offline execution coordination layer.

Capabilities:
- order lifecycle state transitions
- order and execution ID generation
- duplicate execution prevention
- retry policy
- timeout handling
- partial fill handling
- cancel request handling
- execution audit trail
- SHA-256 hashes
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

VERSION = "57.0"
QTY_Q = Decimal("0.000001")
MONEY_Q = Decimal("0.01")
VALID_MODES = {"replay", "paper", "live"}
VALID_ACTIONS = {"BUY", "SELL"}
VALID_STATES = {
    "PENDING",
    "SUBMITTED",
    "PARTIALLY_FILLED",
    "FILLED",
    "CANCEL_REQUESTED",
    "CANCELLED",
    "REJECTED",
    "TIMED_OUT",
}
TERMINAL_STATES = {"FILLED", "CANCELLED", "REJECTED", "TIMED_OUT"}


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


def qty(value: Decimal) -> str:
    return format(value.quantize(QTY_Q, rounding=ROUND_HALF_UP), "f")


def money(value: Decimal) -> str:
    return format(value.quantize(MONEY_Q, rounding=ROUND_HALF_UP), "f")


def parse_utc(value: str, field: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc
    if dt.tzinfo is None:
        raise ValueError(f"{field} must include timezone")
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class ExecutionRequest:
    request_id: str
    symbol: str
    action: str
    quantity: str
    limit_price: str
    risk_approval_sha256: str
    submitted_at_utc: str
    execution_key: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ExecutionConfig:
    max_retries: int
    timeout_seconds: int
    allow_partial_fills: bool
    cancel_on_timeout: bool


@dataclass(frozen=True)
class BrokerEvent:
    event_type: str
    event_time_utc: str
    filled_quantity: str
    fill_price: str
    reason: str


@dataclass(frozen=True)
class LedgerEntry:
    sequence: int
    event_type: str
    request_id: str
    symbol: str
    state: str
    payload_sha256: str
    previous_entry_sha256: str
    entry_sha256: str


@dataclass(frozen=True)
class ExecutionResult:
    schema_version: str
    version: str
    status: str
    decision: str
    request_id: str
    symbol: str
    action: str
    order_id: str
    execution_id: str
    execution_key: str
    final_state: str
    requested_quantity: str
    filled_quantity: str
    remaining_quantity: str
    average_fill_price: str
    retry_count: int
    timed_out: bool
    cancel_requested: bool
    rejection_reasons: list[str]
    request_sha256: str
    execution_sha256: str
    network_used: bool
    audit_trail: list[dict[str, Any]]
    ledger: list[dict[str, Any]]


class TradeExecutionCoordinator:
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
            raise NotImplementedError("live execution transport is intentionally not implemented in V57.0")

    @staticmethod
    def _validate_request(request: ExecutionRequest) -> tuple[str, str, Decimal, Decimal, datetime]:
        symbol = request.symbol.upper().strip()
        action = request.action.upper().strip()
        if not request.request_id.strip():
            raise ValueError("request_id is required")
        if not symbol:
            raise ValueError("symbol is required")
        if action not in VALID_ACTIONS:
            raise ValueError("action must be BUY or SELL")
        quantity = dec(request.quantity, "quantity")
        limit_price = dec(request.limit_price, "limit_price")
        if quantity <= 0:
            raise ValueError("quantity must be greater than zero")
        if limit_price <= 0:
            raise ValueError("limit_price must be greater than zero")
        if len(request.risk_approval_sha256) != 64:
            raise ValueError("risk_approval_sha256 must be 64 characters")
        if not request.execution_key.strip():
            raise ValueError("execution_key is required")
        submitted = parse_utc(request.submitted_at_utc, "submitted_at_utc")
        return symbol, action, quantity, limit_price, submitted

    @staticmethod
    def _validate_config(config: ExecutionConfig) -> None:
        if config.max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if config.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

    @staticmethod
    def _order_id(request: ExecutionRequest) -> str:
        return "ORD-" + canonical_hash({
            "request_id": request.request_id,
            "execution_key": request.execution_key,
            "risk_approval_sha256": request.risk_approval_sha256,
        })[:20].upper()

    @staticmethod
    def _execution_id(request: ExecutionRequest) -> str:
        return "EXE-" + canonical_hash({
            "request_id": request.request_id,
            "symbol": request.symbol.upper().strip(),
            "action": request.action.upper().strip(),
            "quantity": request.quantity,
            "submitted_at_utc": request.submitted_at_utc,
        })[:20].upper()

    def _append_ledger(self, request_id: str, symbol: str, state: str, event_type: str, payload: dict[str, Any]) -> None:
        previous = self.ledger[-1].entry_sha256 if self.ledger else "GENESIS"
        payload_sha = canonical_hash(payload)
        core = {
            "sequence": len(self.ledger) + 1,
            "event_type": event_type,
            "request_id": request_id,
            "symbol": symbol,
            "state": state,
            "payload_sha256": payload_sha,
            "previous_entry_sha256": previous,
        }
        self.ledger.append(LedgerEntry(**core, entry_sha256=canonical_hash(core)))

    def coordinate(
        self,
        request: ExecutionRequest,
        config: ExecutionConfig,
        broker_events: list[BrokerEvent],
        seen_execution_keys: set[str] | None = None,
    ) -> ExecutionResult:
        self._live_gate()
        symbol, action, requested_qty, limit_price, submitted_at = self._validate_request(request)
        self._validate_config(config)
        seen = set(seen_execution_keys or set())

        rejection_reasons: list[str] = []
        audit: list[dict[str, Any]] = []
        order_id = self._order_id(request)
        execution_id = self._execution_id(request)
        retry_count = 0
        timed_out = False
        cancel_requested = False
        state = "PENDING"
        filled_qty = Decimal("0")
        fill_notional = Decimal("0")

        def record(event_type: str, new_state: str, details: dict[str, Any]) -> None:
            nonlocal state
            state = new_state
            item = {
                "sequence": len(audit) + 1,
                "event_type": event_type,
                "state": new_state,
                "details": details,
            }
            audit.append(item)
            self._append_ledger(request.request_id, symbol, new_state, event_type, item)

        if request.execution_key in seen:
            rejection_reasons.append("duplicate_execution")
            record("EXECUTION_REJECTED", "REJECTED", {"reason": "duplicate_execution"})
        else:
            record("ORDER_CREATED", "PENDING", {"order_id": order_id})
            record("ORDER_SUBMITTED", "SUBMITTED", {"execution_id": execution_id})

            last_event_time = submitted_at
            for event in broker_events:
                if state in TERMINAL_STATES:
                    break

                event_time = parse_utc(event.event_time_utc, "event_time_utc")
                if event_time < last_event_time:
                    rejection_reasons.append("broker_event_time_out_of_order")
                    record("EXECUTION_REJECTED", "REJECTED", {"reason": "broker_event_time_out_of_order"})
                    break

                elapsed = (event_time - submitted_at).total_seconds()
                if elapsed > config.timeout_seconds:
                    timed_out = True
                    if config.cancel_on_timeout:
                        cancel_requested = True
                        record("CANCEL_REQUESTED", "CANCEL_REQUESTED", {"reason": "timeout"})
                        record("ORDER_CANCELLED", "CANCELLED", {"reason": "timeout"})
                    else:
                        record("ORDER_TIMED_OUT", "TIMED_OUT", {"reason": "timeout"})
                    break

                event_type = event.event_type.upper().strip()
                event_qty = dec(event.filled_quantity, "filled_quantity")
                fill_price = dec(event.fill_price, "fill_price")

                if event_type == "ACK":
                    record("BROKER_ACK", "SUBMITTED", {})
                elif event_type == "RETRYABLE_ERROR":
                    retry_count += 1
                    if retry_count > config.max_retries:
                        rejection_reasons.append("max_retries_exceeded")
                        record("EXECUTION_REJECTED", "REJECTED", {"reason": "max_retries_exceeded"})
                    else:
                        record("EXECUTION_RETRY", "SUBMITTED", {"retry_count": retry_count, "reason": event.reason})
                elif event_type == "REJECT":
                    rejection_reasons.append(event.reason or "broker_rejected")
                    record("EXECUTION_REJECTED", "REJECTED", {"reason": event.reason or "broker_rejected"})
                elif event_type == "CANCEL_REQUEST":
                    cancel_requested = True
                    record("CANCEL_REQUESTED", "CANCEL_REQUESTED", {"reason": event.reason})
                elif event_type == "CANCELLED":
                    record("ORDER_CANCELLED", "CANCELLED", {"reason": event.reason})
                elif event_type in {"PARTIAL_FILL", "FILL"}:
                    if event_qty <= 0:
                        rejection_reasons.append("fill_quantity_must_be_positive")
                        record("EXECUTION_REJECTED", "REJECTED", {"reason": "fill_quantity_must_be_positive"})
                        break
                    if fill_price <= 0:
                        rejection_reasons.append("fill_price_must_be_positive")
                        record("EXECUTION_REJECTED", "REJECTED", {"reason": "fill_price_must_be_positive"})
                        break
                    if filled_qty + event_qty > requested_qty:
                        rejection_reasons.append("overfill_detected")
                        record("EXECUTION_REJECTED", "REJECTED", {"reason": "overfill_detected"})
                        break
                    if event_type == "PARTIAL_FILL" and not config.allow_partial_fills:
                        rejection_reasons.append("partial_fills_disabled")
                        record("EXECUTION_REJECTED", "REJECTED", {"reason": "partial_fills_disabled"})
                        break

                    filled_qty += event_qty
                    fill_notional += event_qty * fill_price
                    if filled_qty == requested_qty:
                        record("ORDER_FILLED", "FILLED", {
                            "filled_quantity": qty(filled_qty),
                            "fill_price": money(fill_price),
                        })
                    else:
                        record("ORDER_PARTIALLY_FILLED", "PARTIALLY_FILLED", {
                            "filled_quantity": qty(filled_qty),
                            "remaining_quantity": qty(requested_qty - filled_qty),
                            "fill_price": money(fill_price),
                        })
                else:
                    rejection_reasons.append("unsupported_broker_event")
                    record("EXECUTION_REJECTED", "REJECTED", {"reason": "unsupported_broker_event"})
                    break

                last_event_time = event_time

            if state not in TERMINAL_STATES and broker_events:
                last_time = parse_utc(broker_events[-1].event_time_utc, "event_time_utc")
                if (last_time - submitted_at).total_seconds() > config.timeout_seconds:
                    timed_out = True

        remaining_qty = max(Decimal("0"), requested_qty - filled_qty)
        avg_fill = fill_notional / filled_qty if filled_qty > 0 else Decimal("0")

        if state == "FILLED":
            status = "PASS"
            decision = "execution_completed"
        elif state == "PARTIALLY_FILLED":
            status = "PASS"
            decision = "execution_partially_filled"
        elif state == "SUBMITTED":
            status = "PASS"
            decision = "execution_pending"
        elif state == "CANCELLED":
            status = "PASS"
            decision = "execution_cancelled"
        else:
            status = "FAIL"
            decision = "execution_failed"

        request_payload = {
            "request": asdict(request),
            "config": asdict(config),
            "broker_events": [asdict(x) for x in broker_events],
            "seen_execution_keys": sorted(seen),
        }
        request_sha = canonical_hash(request_payload)

        core = {
            "schema_version": "v57.0.trade_execution_coordinator.1",
            "version": VERSION,
            "status": status,
            "decision": decision,
            "request_id": request.request_id,
            "symbol": symbol,
            "action": action,
            "order_id": order_id,
            "execution_id": execution_id,
            "execution_key": request.execution_key,
            "final_state": state,
            "requested_quantity": qty(requested_qty),
            "filled_quantity": qty(filled_qty),
            "remaining_quantity": qty(remaining_qty),
            "average_fill_price": money(avg_fill),
            "retry_count": retry_count,
            "timed_out": timed_out,
            "cancel_requested": cancel_requested,
            "rejection_reasons": rejection_reasons,
            "request_sha256": request_sha,
            "network_used": False,
            "audit_trail": audit,
        }
        execution_sha = canonical_hash(core)

        return ExecutionResult(
            **core,
            execution_sha256=execution_sha,
            ledger=[asdict(x) for x in self.ledger],
        )

    @staticmethod
    def export(path: Path, result: ExecutionResult) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "v57.0.trade_execution_coordinator_export.1",
            "version": VERSION,
            "result": asdict(result),
            "network_used": False,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_payload(path: Path) -> tuple[ExecutionRequest, ExecutionConfig, list[BrokerEvent], set[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return (
        ExecutionRequest(**payload["request"]),
        ExecutionConfig(**payload["config"]),
        [BrokerEvent(**x) for x in payload.get("broker_events", [])],
        set(payload.get("seen_execution_keys", [])),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V57.0 Trade Execution Coordinator Foundation")
    parser.add_argument("--input", required=True)
    parser.add_argument("--mode", choices=sorted(VALID_MODES), default="paper")
    parser.add_argument("--enable-live", action="store_true")
    parser.add_argument("--output", default="release/v57/audit/trade_execution_result_v57_0.json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output)
    try:
        request, config, events, seen = load_payload(Path(args.input))
        coordinator = TradeExecutionCoordinator(mode=args.mode, enable_live=args.enable_live)
        result = coordinator.coordinate(request, config, events, seen)
        coordinator.export(output, result)
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
        return 0 if result.status == "PASS" else 1
    except (TypeError, ValueError, PermissionError, NotImplementedError, json.JSONDecodeError, OSError) as exc:
        error = {
            "schema_version": "v57.0.trade_execution_coordinator_error.1",
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
