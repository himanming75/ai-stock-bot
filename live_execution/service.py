from __future__ import annotations
from decimal import Decimal
from pathlib import Path
from typing import Any

from .dry_run import LiveDryRunTransport
from .idempotency import LiveIdempotencyRegistry
from .ledger import append_ledger
from .models import LiveMicroOrder, canonical_hash
from .risk import authorize_micro_order
from .rollback import build_rollback_plan


def prepare_live_micro_order(
    *,
    root: Path,
    order: LiveMicroOrder,
    estimated_notional: Decimal,
    maximum_order_notional: Decimal,
    daily_order_count: int,
    maximum_daily_orders: int,
    daily_realized_loss: Decimal,
    maximum_daily_loss: Decimal,
    allowed_symbols: tuple[str, ...],
    transport: LiveDryRunTransport,
) -> dict[str, Any]:
    payload = order.payload()
    request_hash = canonical_hash(payload)
    risk = authorize_micro_order(
        estimated_notional=estimated_notional,
        maximum_order_notional=maximum_order_notional,
        daily_order_count=daily_order_count,
        maximum_daily_orders=maximum_daily_orders,
        daily_realized_loss=daily_realized_loss,
        maximum_daily_loss=maximum_daily_loss,
        symbol=order.symbol,
        allowed_symbols=allowed_symbols,
    )
    if not risk["approved"]:
        return {
            "stage": "L3",
            "status": "PASS",
            "state": "LIVE_MICRO_ORDER_BLOCKED",
            "risk": risk,
            "submitted": False,
            "actual_live_orders_submitted": 0,
            "actual_paper_orders_submitted": 0,
        }

    registry = LiveIdempotencyRegistry(
        root / "release/l3_live_micro_execution_preparation/actual/"
               "idempotency_registry.json"
    )
    registry.reserve(request_hash)

    dry_run_result = transport.submit(payload)
    rollback = build_rollback_plan(
        client_order_id=order.client_order_id
    )
    ledger = append_ledger(
        root / "release/l3_live_micro_execution_preparation/actual/"
               "live_order_dry_run_ledger.jsonl",
        {
            "record_type": "LIVE_ORDER_DRY_RUN",
            "request_hash": request_hash,
            "client_order_id": order.client_order_id,
            "symbol": order.symbol.upper(),
            "side": order.side,
        },
    )

    return {
        "stage": "L3",
        "status": "PASS",
        "state": "LIVE_MICRO_EXECUTION_PREPARED",
        "risk": risk,
        "dry_run": dry_run_result,
        "rollback_plan": rollback,
        "ledger_record": ledger,
        "submitted": False,
        "live_network_enabled": False,
        "live_write_enabled": False,
        "actual_live_orders_submitted": 0,
        "actual_paper_orders_submitted": 0,
        "next_fixed_stage": (
            "L3_ACTUAL_MICRO_LIVE_AFTER_P5_AND_L2_ACTUAL_QUALIFICATION"
        ),
    }
