from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .client import AlpacaPaperReadClient
from .credentials import load as load_credentials
from .io import append_jsonl, read_json, write_json
from .lifecycle import build_events
from .normalize import normalize_order, normalize_position
from .reconciliation import reconcile_account, reconcile_positions
from .summary import summarize


ACTUAL = Path("release/v371_01_to_v380_64/actual")
PREVIOUS = ACTUAL / "previous_order_snapshot.json"


def run(
    root: Path,
    allow_network: bool = False,
    client: Any | None = None,
) -> dict:
    credentials = load_credentials()
    account: dict = {}
    positions_raw: list = []
    orders_raw: list = []
    network_used = False
    blocking_reasons: list[str] = []

    if not allow_network:
        blocking_reasons.append("PAPER_NETWORK_NOT_ALLOWED")
    elif not credentials["ready"]:
        blocking_reasons.append("PAPER_CREDENTIALS_MISSING")
    else:
        if client is None:
            client = AlpacaPaperReadClient(credentials["api_key"], credentials["secret_key"])
        account = client.get_account()
        positions_raw = client.get_positions()
        orders_raw = client.get_orders(status="all")
        network_used = True

    positions = [normalize_position(item) for item in positions_raw]
    orders = [normalize_order(item) for item in orders_raw]

    previous_orders = []
    previous_path = root / PREVIOUS
    if previous_path.exists():
        try:
            previous_orders = read_json(previous_path).get("orders", [])
        except Exception:
            previous_orders = []

    events = build_events(previous_orders, orders)
    position_reconciliation = reconcile_positions(orders, positions)
    account_reconciliation = reconcile_account(account, positions) if account else {
        "within_tolerance": False,
        "reason": "ACCOUNT_NOT_LOADED",
    }

    unknown_states = sorted({
        item["status"] for item in orders if not item.get("status_known")
    })

    state = (
        "PAPER_EXECUTION_LIFECYCLE_ACTIVE"
        if network_used
        else "PAPER_EXECUTION_LIFECYCLE_READY_BLOCKED"
    )

    result = {
        "stage": "V380.64",
        "state": state,
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "network_used": network_used,
        "allow_network": allow_network,
        "blocking_reasons": blocking_reasons,
        "account": account,
        "positions": positions,
        "orders": orders,
        "lifecycle_events": events,
        "summary": summarize(orders, events),
        "position_reconciliation": position_reconciliation,
        "account_reconciliation": account_reconciliation,
        "unknown_order_states": unknown_states,
        "read_only": True,
        "paper_endpoint_only": True,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V381_01_TO_V390_64_PORTFOLIO_SYNC_AND_RECOVERY",
    }

    write_json(root / ACTUAL / "latest_lifecycle_result.json", result)
    write_json(root / PREVIOUS, {"orders": orders, "observed_at": result["observed_at"]})
    append_jsonl(root / ACTUAL / "lifecycle_snapshot_ledger.jsonl", result)

    for event in events:
        append_jsonl(root / ACTUAL / "order_lifecycle_event_ledger.jsonl", {
            "observed_at": result["observed_at"],
            **event,
        })

    for order in orders:
        if str(order.get("status")) in {"filled", "partially_filled"}:
            append_jsonl(root / ACTUAL / "fill_ledger.jsonl", {
                "observed_at": result["observed_at"],
                "order_id": order.get("id"),
                "client_order_id": order.get("client_order_id"),
                "symbol": order.get("symbol"),
                "side": order.get("side"),
                "status": order.get("status"),
                "filled_qty": order.get("filled_qty"),
                "filled_avg_price": order.get("filled_avg_price"),
                "filled_at": order.get("filled_at"),
            })

    return result
