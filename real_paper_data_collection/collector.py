from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from real_paper_data_collection.auth import credentials
from real_paper_data_collection.client import AlpacaPaperClient
from real_paper_data_collection.config import load, validate
from real_paper_data_collection.io import load_json, write_json, append_jsonl
from real_paper_data_collection.metrics import calculate
from real_paper_data_collection.normalize import account as normalize_account
from real_paper_data_collection.normalize import order as normalize_order
from real_paper_data_collection.normalize import position as normalize_position
from real_paper_data_collection.reconcile import compare

def collect(root: Path, allow_network: bool = False) -> dict:
    policy = load(root)
    validation = validate(policy)
    auth = credentials()

    blocking = []
    if not validation["valid"]:
        blocking.append("POLICY_INVALID")
    if not policy.get("collector_enabled"):
        blocking.append("COLLECTOR_DISABLED")
    if not policy.get("paper_read_enabled"):
        blocking.append("PAPER_READ_DISABLED")
    if not auth["ready"]:
        blocking.append("PAPER_CREDENTIALS_MISSING")
    if not allow_network:
        blocking.append("NETWORK_NOT_AUTHORIZED")

    raw_account = {}
    raw_clock = {"is_open": False}
    raw_positions = []
    raw_open_orders = []
    raw_closed_orders = []

    if not blocking:
        client = AlpacaPaperClient(auth["key"], auth["secret"], policy["paper_base_url"])
        raw_account = client.account()
        raw_clock = client.clock()
        raw_positions = client.positions()
        raw_open_orders = client.orders("open", int(policy["closed_order_limit"]))
        raw_closed_orders = client.orders("closed", int(policy["closed_order_limit"]))

    account = normalize_account(raw_account) if raw_account else {}
    positions = [normalize_position(row) for row in raw_positions]
    open_orders = [normalize_order(row) for row in raw_open_orders]
    closed_orders = [normalize_order(row) for row in raw_closed_orders]
    all_orders = open_orders + closed_orders

    snapshot = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "market_open": raw_clock.get("is_open") is True,
        "next_open": raw_clock.get("next_open"),
        "next_close": raw_clock.get("next_close"),
        "account": account,
        "positions": positions,
        "orders": all_orders,
        "open_orders": open_orders,
        "closed_orders": closed_orders,
    }
    previous = load_json(
        root / "release/v311_01_to_v320_64/actual/latest_paper_snapshot.json"
    )
    reconciliation = compare(previous, snapshot) if previous else {"change_count": 0, "changes": []}
    metrics = calculate(account, positions, all_orders) if account else {}

    checks = {
        "policy_valid": validation["valid"],
        "paper_endpoint_only": policy.get("paper_base_url") == "https://paper-api.alpaca.markets",
        "credentials_ready": auth["ready"],
        "account_read": bool(account),
        "clock_read": bool(raw_clock),
        "positions_read": isinstance(raw_positions, list),
        "open_orders_read": isinstance(raw_open_orders, list),
        "closed_orders_read": isinstance(raw_closed_orders, list),
        "monitor_only": int(policy.get("maximum_new_orders_per_day", 0)) == 0,
        "paper_submission_disabled": policy.get("paper_submission_enabled") is False,
        "live_submission_disabled": policy.get("live_submission_enabled") is False,
        "live_network_disabled": policy.get("live_network_enabled") is False,
        "broker_write_disabled": policy.get("broker_write_enabled") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    state = (
        "REAL_PAPER_DATA_COLLECTION_ACTIVE"
        if not failed
        else "REAL_PAPER_DATA_COLLECTION_READY_BLOCKED"
    )
    result = {
        "stage": "V320.64",
        "state": state,
        "status": "PASS",
        "blocking_reasons": sorted(set(blocking)),
        "checks": checks,
        "failed": failed,
        "snapshot": snapshot,
        "reconciliation": reconciliation,
        "metrics": metrics,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "next_phase": "V321_01_TO_V330_64_REAL_PAPER_LONG_RUN_QUALIFICATION",
    }

    actual = root / "release/v311_01_to_v320_64/actual"
    write_json(actual / "real_paper_data_collection_result.json", result)
    if account:
        write_json(actual / "latest_paper_snapshot.json", snapshot)
        append_jsonl(actual / "paper_snapshot_ledger.jsonl", snapshot)
        append_jsonl(actual / "paper_metrics_ledger.jsonl", {
            "observed_at": snapshot["observed_at"],
            **metrics,
        })
        if reconciliation["changes"]:
            append_jsonl(actual / "paper_reconciliation_ledger.jsonl", {
                "observed_at": snapshot["observed_at"],
                **reconciliation,
            })
    return result
