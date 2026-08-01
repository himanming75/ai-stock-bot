from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .client import AlpacaPaperClient
from .errors import AlpacaConfigurationError
from .models import BrokerOrder


RECOVERABLE_STATUSES = frozenset({
    "new",
    "accepted",
    "pending_new",
    "partially_filled",
    "pending_cancel",
    "pending_replace",
    "held",
    "calculated",
})
TERMINAL_STATUSES = frozenset({
    "filled",
    "canceled",
    "expired",
    "rejected",
    "done_for_day",
})


@dataclass(frozen=True)
class PaperOrderRecoveryRecord:
    schema_version: int
    saved_at: datetime
    client_order_id: str
    broker_order_id: str | None
    symbol: str
    side: str
    requested_quantity: Decimal
    last_filled_quantity: Decimal
    last_status: str
    submission_confirmed: bool
    terminal: bool
    recovery_generation: int

    def validate(self) -> None:
        if self.schema_version != 1:
            raise AlpacaConfigurationError("unsupported recovery schema")
        if not self.client_order_id.startswith("BOT-PAPER-ONE-"):
            raise AlpacaConfigurationError("invalid recovery client_order_id")
        if not self.symbol:
            raise AlpacaConfigurationError("recovery symbol is required")
        if self.side not in {"buy", "sell"}:
            raise AlpacaConfigurationError("invalid recovery side")
        if self.requested_quantity <= 0:
            raise AlpacaConfigurationError("requested quantity must be positive")
        if self.last_filled_quantity < 0:
            raise AlpacaConfigurationError("filled quantity cannot be negative")
        if self.last_filled_quantity > self.requested_quantity:
            raise AlpacaConfigurationError("filled quantity exceeds requested quantity")
        if self.recovery_generation < 0:
            raise AlpacaConfigurationError("recovery generation cannot be negative")

    def to_json_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["saved_at"] = self.saved_at.isoformat()
        raw["requested_quantity"] = str(self.requested_quantity)
        raw["last_filled_quantity"] = str(self.last_filled_quantity)
        return raw

    @classmethod
    def from_json_dict(cls, raw: dict[str, Any]) -> "PaperOrderRecoveryRecord":
        record = cls(
            schema_version=int(raw["schema_version"]),
            saved_at=datetime.fromisoformat(str(raw["saved_at"])),
            client_order_id=str(raw["client_order_id"]),
            broker_order_id=(
                None if raw.get("broker_order_id") is None
                else str(raw["broker_order_id"])
            ),
            symbol=str(raw["symbol"]).upper(),
            side=str(raw["side"]).lower(),
            requested_quantity=Decimal(str(raw["requested_quantity"])),
            last_filled_quantity=Decimal(str(raw["last_filled_quantity"])),
            last_status=str(raw["last_status"]).lower(),
            submission_confirmed=bool(raw["submission_confirmed"]),
            terminal=bool(raw["terminal"]),
            recovery_generation=int(raw["recovery_generation"]),
        )
        record.validate()
        return record


class AtomicPaperOrderRecoveryStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def save(self, record: PaperOrderRecoveryRecord) -> None:
        record.validate()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            record.to_json_dict(),
            indent=2,
            sort_keys=True,
        ) + "\n"
        fd, temp_name = tempfile.mkstemp(
            prefix=self.path.name + ".",
            suffix=".tmp",
            dir=str(self.path.parent),
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def load(self) -> PaperOrderRecoveryRecord | None:
        if not self.path.exists():
            return None
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AlpacaConfigurationError("invalid recovery file") from exc
        if not isinstance(raw, dict):
            raise AlpacaConfigurationError("recovery document must be an object")
        return PaperOrderRecoveryRecord.from_json_dict(raw)


@dataclass(frozen=True)
class PaperOrderRecoveryReport:
    generated_at: datetime
    client_order_id: str
    previous_status: str
    recovered_status: str
    previous_filled_quantity: Decimal
    recovered_filled_quantity: Decimal
    terminal: bool
    recovery_generation: int
    duplicate_submission_prevented: bool
    restart_read_only: bool
    network_requests_executed: int
    write_requests_executed: int
    additional_orders_submitted: int
    live_orders_submitted: int = 0

    def to_json_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        for key, value in tuple(raw.items()):
            if isinstance(value, Decimal):
                raw[key] = str(value)
            elif isinstance(value, datetime):
                raw[key] = value.isoformat()
        return raw


class AlpacaPaperOrderRecoveryManager:
    """Restores one known Paper order through GET-only reconciliation."""

    def __init__(
        self,
        *,
        client: AlpacaPaperClient,
        store: AtomicPaperOrderRecoveryStore,
    ) -> None:
        if client.config.network_write_enabled:
            raise AlpacaConfigurationError(
                "recovery client must have write network disabled"
            )
        if not client.config.network_read_enabled:
            raise AlpacaConfigurationError(
                "recovery client requires read network"
            )
        self.client = client
        self.store = store

    def checkpoint_from_order(
        self,
        order: BrokerOrder,
        *,
        generation: int = 0,
    ) -> PaperOrderRecoveryRecord:
        status = order.status.lower()
        record = PaperOrderRecoveryRecord(
            schema_version=1,
            saved_at=datetime.now(timezone.utc),
            client_order_id=order.client_order_id,
            broker_order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            requested_quantity=order.quantity,
            last_filled_quantity=order.filled_quantity,
            last_status=status,
            submission_confirmed=True,
            terminal=status in TERMINAL_STATUSES,
            recovery_generation=generation,
        )
        self.store.save(record)
        return record

    def recover(self) -> PaperOrderRecoveryReport:
        previous = self.store.load()
        if previous is None:
            raise AlpacaConfigurationError("no recovery checkpoint exists")
        previous.validate()

        if not previous.submission_confirmed:
            raise AlpacaConfigurationError(
                "unconfirmed submission cannot be automatically recovered"
            )

        order = self.client.get_order_by_client_id(previous.client_order_id)
        if order.symbol != previous.symbol:
            raise AlpacaConfigurationError("recovered symbol mismatch")
        if order.side != previous.side:
            raise AlpacaConfigurationError("recovered side mismatch")
        if order.quantity != previous.requested_quantity:
            raise AlpacaConfigurationError("recovered quantity mismatch")
        if order.filled_quantity < previous.last_filled_quantity:
            raise AlpacaConfigurationError("filled quantity moved backwards")

        status = order.status.lower()
        terminal = status in TERMINAL_STATUSES
        if not terminal and status not in RECOVERABLE_STATUSES:
            raise AlpacaConfigurationError(f"unknown recovered order status: {status}")

        recovered = PaperOrderRecoveryRecord(
            schema_version=1,
            saved_at=datetime.now(timezone.utc),
            client_order_id=order.client_order_id,
            broker_order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            requested_quantity=order.quantity,
            last_filled_quantity=order.filled_quantity,
            last_status=status,
            submission_confirmed=True,
            terminal=terminal,
            recovery_generation=previous.recovery_generation + 1,
        )
        self.store.save(recovered)

        return PaperOrderRecoveryReport(
            generated_at=datetime.now(timezone.utc),
            client_order_id=recovered.client_order_id,
            previous_status=previous.last_status,
            recovered_status=recovered.last_status,
            previous_filled_quantity=previous.last_filled_quantity,
            recovered_filled_quantity=recovered.last_filled_quantity,
            terminal=recovered.terminal,
            recovery_generation=recovered.recovery_generation,
            duplicate_submission_prevented=True,
            restart_read_only=True,
            network_requests_executed=self.client.network_requests_executed,
            write_requests_executed=self.client.write_requests_executed,
            additional_orders_submitted=0,
        )
