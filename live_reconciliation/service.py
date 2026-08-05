from __future__ import annotations
from decimal import Decimal
from pathlib import Path
from typing import Any

from .drift import compare_cash, compare_order, compare_positions
from .fill_registry import LiveFillRegistry
from .ledger import append_reconciliation_event
from .models import OrderState, PositionState
from .recovery import build_manual_repair_plan


def reconcile_offline_fixture(
    *,
    root: Path,
    expected_order: dict[str, Any],
    actual_order: dict[str, Any],
    expected_positions: list[dict[str, Any]],
    actual_positions: list[dict[str, Any]],
    expected_cash: Decimal,
    actual_cash: Decimal,
    expected_buying_power: Decimal,
    actual_buying_power: Decimal,
    fill_key: str,
) -> dict[str, Any]:
    registry = LiveFillRegistry(
        root / "release/l4_live_reconciliation_preparation/actual/"
               "fill_registry.json"
    )
    registry.reserve(fill_key)

    order_result = compare_order(
        expected_order,
        OrderState.from_dict(actual_order),
    )
    position_result = compare_positions(
        [PositionState.from_dict(item) for item in expected_positions],
        [PositionState.from_dict(item) for item in actual_positions],
    )
    cash_result = compare_cash(
        expected_cash=expected_cash,
        actual_cash=actual_cash,
        expected_buying_power=expected_buying_power,
        actual_buying_power=actual_buying_power,
    )

    drift_types = []
    if order_result["drift_detected"]:
        drift_types.append("order")
    if position_result["drift_detected"]:
        drift_types.append("position")
    if cash_result["drift_detected"]:
        drift_types.append("cash")

    repair_plan = build_manual_repair_plan(drift_types)
    event = append_reconciliation_event(
        root / "release/l4_live_reconciliation_preparation/actual/"
               "reconciliation_ledger.jsonl",
        {
            "record_type": "LIVE_RECONCILIATION_DRY_RUN",
            "fill_key": fill_key,
            "drift_types": drift_types,
        },
    )

    return {
        "stage": "L4",
        "status": "PASS",
        "state": (
            "LIVE_RECONCILIATION_PREPARED"
            if not drift_types
            else "LIVE_RECONCILIATION_DRIFT_DETECTED"
        ),
        "order_reconciliation": order_result,
        "position_reconciliation": position_result,
        "cash_reconciliation": cash_result,
        "repair_plan": repair_plan,
        "ledger_record": event,
        "actual_live_reconciliation_performed": False,
        "actual_live_reconciliation_allowed": False,
        "live_network_enabled": False,
        "live_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_stage": (
            "L4_ACTUAL_AFTER_L3_ACTUAL_MICRO_LIVE"
        ),
    }
