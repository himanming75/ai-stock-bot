from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from .adapter_models import (
    CancelRequest,
    CancelResult,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    FillRecord,
)


class ExecutionTransport(Protocol):
    def submit(self, request: ExecutionRequest, now: datetime) -> ExecutionResult:
        ...

    def cancel(self, request: CancelRequest, now: datetime) -> CancelResult:
        ...


@dataclass
class MockPaperTransport:
    """Deterministic in-memory paper transport. Never performs network I/O."""

    default_fill_price: Decimal = Decimal("50")
    reject_symbols: set[str] = None
    partial_fill_ratio: Decimal = Decimal("0.5")

    def __post_init__(self) -> None:
        if self.reject_symbols is None:
            self.reject_symbols = set()
        if not Decimal("0") < self.partial_fill_ratio < Decimal("1"):
            raise ValueError("partial_fill_ratio must be between 0 and 1")
        self.requests: list[ExecutionRequest] = []
        self.results: dict[str, ExecutionResult] = {}
        self.cancel_requests: list[CancelRequest] = []

    def submit(self, request: ExecutionRequest, now: datetime) -> ExecutionResult:
        request.validate()
        self.requests.append(request)

        if request.symbol in self.reject_symbols:
            result = ExecutionResult(
                request_id=request.request_id,
                client_order_id=request.client_order_id,
                broker_order_id=None,
                status=ExecutionStatus.REJECTED,
                requested_quantity=request.quantity,
                filled_quantity=Decimal("0"),
                average_fill_price=None,
                updated_at=now,
                rejection_reason="symbol_rejected_by_mock_transport",
            )
            result.validate()
            self.results[request.client_order_id] = result
            return result

        result = ExecutionResult(
            request_id=request.request_id,
            client_order_id=request.client_order_id,
            broker_order_id="MOCK-" + uuid4().hex[:16],
            status=ExecutionStatus.ACCEPTED,
            requested_quantity=request.quantity,
            filled_quantity=Decimal("0"),
            average_fill_price=None,
            updated_at=now,
        )
        result.validate()
        self.results[request.client_order_id] = result
        return result

    def simulate_partial_fill(self, client_order_id: str, now: datetime) -> ExecutionResult:
        current = self.results[client_order_id]
        quantity = current.requested_quantity * self.partial_fill_ratio
        fill = FillRecord(quantity, self.default_fill_price, now)
        fill.validate()
        result = ExecutionResult(
            request_id=current.request_id,
            client_order_id=current.client_order_id,
            broker_order_id=current.broker_order_id,
            status=ExecutionStatus.PARTIALLY_FILLED,
            requested_quantity=current.requested_quantity,
            filled_quantity=quantity,
            average_fill_price=self.default_fill_price,
            updated_at=now,
            fills=(fill,),
        )
        result.validate()
        self.results[client_order_id] = result
        return result

    def simulate_full_fill(self, client_order_id: str, now: datetime) -> ExecutionResult:
        current = self.results[client_order_id]
        remaining = current.requested_quantity - current.filled_quantity
        fills = list(current.fills)
        if remaining > 0:
            fill = FillRecord(remaining, self.default_fill_price, now)
            fill.validate()
            fills.append(fill)
        total_notional = sum((fill.quantity * fill.price for fill in fills), Decimal("0"))
        average = total_notional / current.requested_quantity
        result = ExecutionResult(
            request_id=current.request_id,
            client_order_id=current.client_order_id,
            broker_order_id=current.broker_order_id,
            status=ExecutionStatus.FILLED,
            requested_quantity=current.requested_quantity,
            filled_quantity=current.requested_quantity,
            average_fill_price=average,
            updated_at=now,
            fills=tuple(fills),
        )
        result.validate()
        self.results[client_order_id] = result
        return result

    def cancel(self, request: CancelRequest, now: datetime) -> CancelResult:
        request.validate()
        self.cancel_requests.append(request)
        result = CancelResult(
            client_order_id=request.client_order_id,
            status=ExecutionStatus.CANCELED,
            canceled_at=now,
            reason=request.reason,
        )
        result.validate()
        return result
