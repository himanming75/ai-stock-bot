from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any


class ExecutionStatus(str, Enum):
    NEW = "NEW"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELED = "CANCELED"


@dataclass(frozen=True)
class ExecutionRequest:
    request_id: str
    client_order_id: str
    intent_id: str
    symbol: str
    side: str
    quantity: Decimal
    order_type: str
    time_in_force: str
    created_at: datetime
    payload: dict[str, Any]

    def validate(self) -> None:
        if not self.request_id or not self.client_order_id or not self.intent_id:
            raise ValueError("request identifiers are required")
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("symbol must be uppercase")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")


@dataclass(frozen=True)
class FillRecord:
    quantity: Decimal
    price: Decimal
    filled_at: datetime

    def validate(self) -> None:
        if self.quantity <= 0 or self.price <= 0:
            raise ValueError("fill values must be positive")
        if self.filled_at.tzinfo is None:
            raise ValueError("filled_at must be timezone-aware")


@dataclass(frozen=True)
class ExecutionResult:
    request_id: str
    client_order_id: str
    broker_order_id: str | None
    status: ExecutionStatus
    requested_quantity: Decimal
    filled_quantity: Decimal
    average_fill_price: Decimal | None
    updated_at: datetime
    fills: tuple[FillRecord, ...] = ()
    rejection_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.request_id or not self.client_order_id:
            raise ValueError("result identifiers are required")
        if self.requested_quantity <= 0:
            raise ValueError("requested_quantity must be positive")
        if self.filled_quantity < 0 or self.filled_quantity > self.requested_quantity:
            raise ValueError("invalid filled_quantity")
        if self.updated_at.tzinfo is None:
            raise ValueError("updated_at must be timezone-aware")
        if self.status == ExecutionStatus.REJECTED and not self.rejection_reason:
            raise ValueError("rejected result requires reason")
        if self.status == ExecutionStatus.FILLED and self.filled_quantity != self.requested_quantity:
            raise ValueError("FILLED result must be fully filled")
        if self.status == ExecutionStatus.PARTIALLY_FILLED:
            if not Decimal("0") < self.filled_quantity < self.requested_quantity:
                raise ValueError("PARTIALLY_FILLED requires partial quantity")


@dataclass(frozen=True)
class CancelRequest:
    client_order_id: str
    requested_at: datetime
    reason: str = "USER_REQUEST"

    def validate(self) -> None:
        if not self.client_order_id:
            raise ValueError("client_order_id is required")
        if self.requested_at.tzinfo is None:
            raise ValueError("requested_at must be timezone-aware")


@dataclass(frozen=True)
class CancelResult:
    client_order_id: str
    status: ExecutionStatus
    canceled_at: datetime
    reason: str

    def validate(self) -> None:
        if self.status != ExecutionStatus.CANCELED:
            raise ValueError("cancel result must have CANCELED status")
        if self.canceled_at.tzinfo is None:
            raise ValueError("canceled_at must be timezone-aware")


@dataclass(frozen=True)
class ReconciliationRecord:
    client_order_id: str
    request_status: ExecutionStatus
    transport_status: ExecutionStatus
    matched: bool
    checked_at: datetime
    details: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.client_order_id:
            raise ValueError("client_order_id is required")
        if self.checked_at.tzinfo is None:
            raise ValueError("checked_at must be timezone-aware")
