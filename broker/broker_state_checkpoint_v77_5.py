from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Any

from broker.execution_event_reconciliation_v77_4 import (
    ExecutionEventReconciler,
    ReconciliationReport,
)
from broker.order_lifecycle_simulator_v77_3 import OrderLifecycleSimulator


class CheckpointError(ValueError):
    """Raised when a broker state checkpoint is invalid or cannot be verified."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BrokerStateCheckpoint:
    schema_version: str
    checkpoint_id: str
    source_reconciliation_status: str
    source_reconciliation_issue_count: int
    starting_cash: str
    cash: str
    buying_power: str
    equity: str
    positions: tuple[MappingProxyType, ...]
    orders: tuple[MappingProxyType, ...]
    fills: tuple[MappingProxyType, ...]
    events: tuple[MappingProxyType, ...]
    state_sha256: str

    def unsigned_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "checkpoint_id": self.checkpoint_id,
            "source_reconciliation_status": self.source_reconciliation_status,
            "source_reconciliation_issue_count": self.source_reconciliation_issue_count,
            "starting_cash": self.starting_cash,
            "cash": self.cash,
            "buying_power": self.buying_power,
            "equity": self.equity,
            "positions": [dict(item) for item in self.positions],
            "orders": [dict(item) for item in self.orders],
            "fills": [dict(item) for item in self.fills],
            "events": [dict(item) for item in self.events],
        }

    def as_dict(self) -> dict[str, Any]:
        payload = self.unsigned_payload()
        payload["state_sha256"] = self.state_sha256
        return payload


class BrokerStateCheckpointManager:
    SCHEMA_VERSION = "v77.5.broker_state_checkpoint.1"

    def __init__(
        self,
        reconciler: ExecutionEventReconciler | None = None,
    ) -> None:
        self._reconciler = reconciler or ExecutionEventReconciler()

    def create(
        self,
        simulator: OrderLifecycleSimulator,
        *,
        checkpoint_id: str,
    ) -> BrokerStateCheckpoint:
        checkpoint_id = checkpoint_id.strip()
        if not checkpoint_id:
            raise CheckpointError("checkpoint_id is required")

        report = self._reconciler.reconcile(simulator)
        if not report.passed:
            raise CheckpointError(
                f"cannot checkpoint unreconciled state: {report.issue_count} issue(s)"
            )

        snapshot = simulator.get_account_snapshot()
        positions = tuple(
            MappingProxyType(
                {
                    "symbol": position.symbol,
                    "quantity": str(position.quantity),
                    "average_entry_price": str(position.average_entry_price),
                    "market_value": str(position.market_value),
                    "unrealized_pnl": str(position.unrealized_pnl),
                }
            )
            for position in snapshot.positions
        )
        orders = tuple(
            MappingProxyType(
                {
                    "broker_order_id": order.broker_order_id,
                    "client_order_id": order.request.client_order_id,
                    "symbol": order.request.symbol,
                    "side": order.request.side.value,
                    "quantity": str(order.request.quantity),
                    "status": order.status.value,
                    "filled_quantity": str(order.filled_quantity),
                    "average_fill_price": (
                        str(order.average_fill_price)
                        if order.average_fill_price is not None
                        else None
                    ),
                    "submitted_at_utc": order.submitted_at_utc.isoformat(),
                    "updated_at_utc": order.updated_at_utc.isoformat(),
                }
            )
            for order in simulator.list_orders()
        )
        fills = tuple(
            MappingProxyType(fill.as_dict())
            for fill in simulator.list_fills()
        )
        events = tuple(
            MappingProxyType(event.as_dict())
            for event in simulator.event_ledger()
        )

        unsigned = {
            "schema_version": self.SCHEMA_VERSION,
            "checkpoint_id": checkpoint_id,
            "source_reconciliation_status": report.status,
            "source_reconciliation_issue_count": report.issue_count,
            "starting_cash": str(simulator._starting_cash),
            "cash": str(snapshot.cash),
            "buying_power": str(snapshot.buying_power),
            "equity": str(snapshot.equity),
            "positions": [dict(item) for item in positions],
            "orders": [dict(item) for item in orders],
            "fills": [dict(item) for item in fills],
            "events": [dict(item) for item in events],
        }
        return BrokerStateCheckpoint(
            schema_version=self.SCHEMA_VERSION,
            checkpoint_id=checkpoint_id,
            source_reconciliation_status=report.status,
            source_reconciliation_issue_count=report.issue_count,
            starting_cash=str(simulator._starting_cash),
            cash=str(snapshot.cash),
            buying_power=str(snapshot.buying_power),
            equity=str(snapshot.equity),
            positions=positions,
            orders=orders,
            fills=fills,
            events=events,
            state_sha256=sha256_json(unsigned),
        )

    def verify(self, checkpoint: BrokerStateCheckpoint) -> bool:
        if checkpoint.schema_version != self.SCHEMA_VERSION:
            return False
        if checkpoint.source_reconciliation_status != "PASS":
            return False
        if checkpoint.source_reconciliation_issue_count != 0:
            return False
        return checkpoint.state_sha256 == sha256_json(checkpoint.unsigned_payload())

    def write(self, checkpoint: BrokerStateCheckpoint, path: Path) -> None:
        if not self.verify(checkpoint):
            raise CheckpointError("refusing to write invalid checkpoint")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(checkpoint.as_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def read(self, path: Path) -> BrokerStateCheckpoint:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise CheckpointError(f"checkpoint not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise CheckpointError(f"checkpoint JSON invalid: {path}") from exc
        if not isinstance(value, dict):
            raise CheckpointError("checkpoint root must be object")

        required = {
            "schema_version",
            "checkpoint_id",
            "source_reconciliation_status",
            "source_reconciliation_issue_count",
            "starting_cash",
            "cash",
            "buying_power",
            "equity",
            "positions",
            "orders",
            "fills",
            "events",
            "state_sha256",
        }
        missing = sorted(required - set(value))
        if missing:
            raise CheckpointError(f"checkpoint missing fields: {', '.join(missing)}")

        checkpoint = BrokerStateCheckpoint(
            schema_version=str(value["schema_version"]),
            checkpoint_id=str(value["checkpoint_id"]),
            source_reconciliation_status=str(value["source_reconciliation_status"]),
            source_reconciliation_issue_count=int(
                value["source_reconciliation_issue_count"]
            ),
            starting_cash=str(value["starting_cash"]),
            cash=str(value["cash"]),
            buying_power=str(value["buying_power"]),
            equity=str(value["equity"]),
            positions=tuple(
                MappingProxyType(dict(item)) for item in value["positions"]
            ),
            orders=tuple(
                MappingProxyType(dict(item)) for item in value["orders"]
            ),
            fills=tuple(
                MappingProxyType(dict(item)) for item in value["fills"]
            ),
            events=tuple(
                MappingProxyType(dict(item)) for item in value["events"]
            ),
            state_sha256=str(value["state_sha256"]),
        )
        if not self.verify(checkpoint):
            raise CheckpointError("checkpoint integrity verification failed")
        return checkpoint
