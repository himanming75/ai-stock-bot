from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence


class OrderOwnership(str, Enum):
    BOT = "BOT"
    EXTERNAL = "EXTERNAL"
    UNKNOWN = "UNKNOWN"


class OrderIdentityStatus(str, Enum):
    MATCHED = "MATCHED"
    SAFE_MODE = "SAFE_MODE"
    NO_OPEN_ORDERS = "NO_OPEN_ORDERS"


@dataclass(frozen=True)
class OrderIdentityRecord:
    broker_order_id: str
    client_order_id: str
    symbol: str
    side: str
    quantity: str
    order_type: str
    time_in_force: str
    status: str
    submitted_at: str
    filled_quantity: str
    limit_price: str | None
    ownership: OrderOwnership
    recognized_internal_order: bool
    blocking: bool
    reason: str

    def to_json_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["ownership"] = self.ownership.value
        return raw


@dataclass(frozen=True)
class OrderIdentityReport:
    status: OrderIdentityStatus
    safe_mode_engaged: bool
    autonomous_order_allowed: bool
    open_order_count: int
    bot_order_count: int
    external_order_count: int
    unknown_order_count: int
    recognized_internal_order_count: int
    blocking_order_count: int
    records: tuple[OrderIdentityRecord, ...]
    read_requests_executed: int
    write_requests_executed: int
    actual_paper_orders_submitted: int
    live_orders_submitted: int

    def to_json_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["status"] = self.status.value
        raw["records"] = [item.to_json_dict() for item in self.records]
        return raw


@dataclass(frozen=True)
class OrderIdentityPolicy:
    bot_client_order_prefixes: tuple[str, ...] = (
        "BOT-AUTO-PAPER-",
        "AI-STOCK-BOT-PAPER-",
        "BOT-PAPER-",
    )
    approved_symbols: tuple[str, ...] = ("AAPL", "SPY", "QQQ")
    allowed_sides: tuple[str, ...] = ("BUY", "SELL")
    block_external_orders: bool = True
    block_unknown_orders: bool = True
    block_unrecognized_bot_orders: bool = True

    def validate(self) -> None:
        if not self.bot_client_order_prefixes:
            raise ValueError("at least one bot client_order_id prefix is required")
        if any(not item.strip() for item in self.bot_client_order_prefixes):
            raise ValueError("empty bot prefix is not allowed")
        if not self.approved_symbols:
            raise ValueError("approved_symbols cannot be empty")


class AutonomousPaperOrderIdentityReconciler:
    """Classifies actual Alpaca Paper open orders and applies ownership gates."""

    def __init__(self, *, policy: OrderIdentityPolicy | None = None) -> None:
        self.policy = policy or OrderIdentityPolicy()
        self.policy.validate()

    def reconcile(
        self,
        *,
        open_orders: Sequence[Mapping[str, Any]],
        internal_order_ledger: Sequence[Mapping[str, Any]],
    ) -> OrderIdentityReport:
        ledger_client_ids = {
            str(item.get("client_order_id", "")).strip()
            for item in internal_order_ledger
            if str(item.get("client_order_id", "")).strip()
        }
        ledger_broker_ids = {
            str(item.get("broker_order_id", "")).strip()
            for item in internal_order_ledger
            if str(item.get("broker_order_id", "")).strip()
        }

        records: list[OrderIdentityRecord] = []
        for raw in open_orders:
            broker_order_id = _text(raw, "id", "broker_order_id", "order_id")
            client_order_id = _text(raw, "client_order_id")
            symbol = _text(raw, "symbol").upper()
            side = _text(raw, "side").upper()
            quantity = _text(raw, "qty", "quantity")
            order_type = _text(raw, "type", "order_type").upper()
            time_in_force = _text(raw, "time_in_force").upper()
            status = _text(raw, "status").upper()
            submitted_at = _text(raw, "submitted_at")
            filled_quantity = _text(raw, "filled_qty", "filled_quantity") or "0"
            limit_price = _optional_text(raw, "limit_price")

            ownership = self._ownership(client_order_id)
            recognized = (
                client_order_id in ledger_client_ids
                or (broker_order_id and broker_order_id in ledger_broker_ids)
            )

            blocking, reason = self._blocking_reason(
                ownership=ownership,
                recognized=recognized,
                symbol=symbol,
                side=side,
            )
            records.append(OrderIdentityRecord(
                broker_order_id=broker_order_id,
                client_order_id=client_order_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                time_in_force=time_in_force,
                status=status,
                submitted_at=submitted_at,
                filled_quantity=filled_quantity,
                limit_price=limit_price,
                ownership=ownership,
                recognized_internal_order=recognized,
                blocking=blocking,
                reason=reason,
            ))

        bot_count = sum(1 for item in records if item.ownership == OrderOwnership.BOT)
        external_count = sum(
            1 for item in records if item.ownership == OrderOwnership.EXTERNAL
        )
        unknown_count = sum(
            1 for item in records if item.ownership == OrderOwnership.UNKNOWN
        )
        recognized_count = sum(1 for item in records if item.recognized_internal_order)
        blocking_count = sum(1 for item in records if item.blocking)
        safe_mode = blocking_count > 0

        if not records:
            status = OrderIdentityStatus.NO_OPEN_ORDERS
        elif safe_mode:
            status = OrderIdentityStatus.SAFE_MODE
        else:
            status = OrderIdentityStatus.MATCHED

        return OrderIdentityReport(
            status=status,
            safe_mode_engaged=safe_mode,
            autonomous_order_allowed=not safe_mode,
            open_order_count=len(records),
            bot_order_count=bot_count,
            external_order_count=external_count,
            unknown_order_count=unknown_count,
            recognized_internal_order_count=recognized_count,
            blocking_order_count=blocking_count,
            records=tuple(records),
            read_requests_executed=0,
            write_requests_executed=0,
            actual_paper_orders_submitted=0,
            live_orders_submitted=0,
        )

    def _ownership(self, client_order_id: str) -> OrderOwnership:
        value = client_order_id.strip()
        if not value:
            return OrderOwnership.UNKNOWN
        if any(value.startswith(prefix) for prefix in self.policy.bot_client_order_prefixes):
            return OrderOwnership.BOT
        return OrderOwnership.EXTERNAL

    def _blocking_reason(
        self,
        *,
        ownership: OrderOwnership,
        recognized: bool,
        symbol: str,
        side: str,
    ) -> tuple[bool, str]:
        if symbol not in self.policy.approved_symbols:
            return True, "order symbol is outside the approved autonomous list"
        if side not in self.policy.allowed_sides:
            return True, "order side is unsupported"

        if ownership == OrderOwnership.EXTERNAL:
            return (
                self.policy.block_external_orders,
                "external or manual order requires operator review",
            )
        if ownership == OrderOwnership.UNKNOWN:
            return (
                self.policy.block_unknown_orders,
                "order ownership cannot be determined",
            )
        if ownership == OrderOwnership.BOT and not recognized:
            return (
                self.policy.block_unrecognized_bot_orders,
                "bot-prefixed order is absent from the internal ledger",
            )
        return False, "recognized internal bot order"


def _text(raw: Mapping[str, Any], *names: str) -> str:
    for name in names:
        value = raw.get(name)
        if value is not None:
            return str(value).strip()
    return ""


def _optional_text(raw: Mapping[str, Any], *names: str) -> str | None:
    value = _text(raw, *names)
    return value if value else None
