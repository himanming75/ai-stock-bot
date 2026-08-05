from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from .execution_config import ExecutionConfig
from .execution_models import (
    CanonicalOrderRequest,
    canonical_hash,
    order_request_hash,
)
from .idempotency import reserve, update
from .io import append_jsonl, write_json
from .safety_checks import evaluate_pre_submit


def submit_paper_order(
    *,
    config: ExecutionConfig,
    order: CanonicalOrderRequest,
    account: dict[str, Any],
    asset: dict[str, Any],
    clock: dict[str, Any],
    kill_switch: dict[str, Any],
    risk_permission: bool,
    latest_trade_price: Decimal | None,
    positions: list[dict[str, Any]],
    registry_path: Path,
    order_ledger_path: Path,
    error_ledger_path: Path,
    http: Any,
) -> dict[str, Any]:
    payload = order.as_payload()
    request_hash = order_request_hash(order)

    pre_submit = evaluate_pre_submit(
        config=config,
        order=order,
        account=account,
        asset=asset,
        clock=clock,
        kill_switch=kill_switch,
        risk_permission=risk_permission,
        latest_trade_price=latest_trade_price,
        positions=positions,
        registry_path=registry_path,
    )

    if not pre_submit["approved"]:
        result = {
            "stage": "P2",
            "state": "PAPER_ORDER_BLOCKED",
            "status": "PASS",
            "submitted": False,
            "client_order_id": order.client_order_id,
            "request_hash": request_hash,
            "pre_submit": pre_submit,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
        }
        append_jsonl(error_ledger_path, result)
        return result

    reserve(registry_path, order.client_order_id, request_hash)

    request_record = {
        "record_type": "ORDER_REQUEST",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "client_order_id": order.client_order_id,
        "request_hash": request_hash,
        "payload": payload,
        "pre_submit": pre_submit,
    }
    append_jsonl(order_ledger_path, request_record)

    try:
        response, request_id = http.submit_order(payload)
    except Exception as exc:
        update(
            registry_path,
            order.client_order_id,
            state="SUBMISSION_ERROR",
            error=str(exc),
        )
        error_record = {
            "record_type": "ORDER_SUBMISSION_ERROR",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "client_order_id": order.client_order_id,
            "request_hash": request_hash,
            "error": str(exc),
        }
        append_jsonl(error_ledger_path, error_record)
        raise

    broker_order_id = str(response.get("id", ""))
    response_hash = canonical_hash(response)
    update(
        registry_path,
        order.client_order_id,
        state="SUBMITTED",
        broker_order_id=broker_order_id,
        response_hash=response_hash,
        request_id=request_id,
        submitted_at=datetime.now(timezone.utc).isoformat(),
    )

    response_record = {
        "record_type": "ORDER_RESPONSE",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "client_order_id": order.client_order_id,
        "broker_order_id": broker_order_id,
        "request_id": request_id,
        "request_hash": request_hash,
        "response_hash": response_hash,
        "response": response,
    }
    append_jsonl(order_ledger_path, response_record)

    result = {
        "stage": "P2",
        "state": "ALPACA_PAPER_ORDER_SUBMITTED",
        "status": "PASS",
        "submitted": True,
        "client_order_id": order.client_order_id,
        "broker_order_id": broker_order_id,
        "request_id": request_id,
        "request_hash": request_hash,
        "response_hash": response_hash,
        "pre_submit": pre_submit,
        "actual_paper_orders_submitted": 1,
        "actual_live_orders_submitted": 0,
        "next_fixed_stage": "P3_ORDER_FILL_PORTFOLIO_SYNC",
    }
    return result
