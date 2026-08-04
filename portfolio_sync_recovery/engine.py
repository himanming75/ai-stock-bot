from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from .client import AlpacaPaperReadClient
from .credentials import load as load_credentials
from .drift import compare_accounts, compare_positions
from .health import classify
from .io import append_jsonl, read_json, write_json
from .normalize import account as normalize_account, position as normalize_position
from .recovery import build_plan


ACTUAL = Path("release/v381_01_to_v390_64/actual")
SNAPSHOT = ACTUAL / "portfolio_sync_snapshot.json"


def run(
    root: Path,
    policy: dict,
    allow_network: bool = False,
    client: Any | None = None,
) -> dict:
    credentials = load_credentials()
    blocking_reasons: list[str] = []
    network_used = False
    raw_account: dict = {}
    raw_positions: list = []
    open_orders: list = []

    if not allow_network:
        blocking_reasons.append("PAPER_NETWORK_NOT_ALLOWED")
    elif not credentials["ready"]:
        blocking_reasons.append("PAPER_CREDENTIALS_MISSING")
    else:
        if client is None:
            client = AlpacaPaperReadClient(credentials["api_key"], credentials["secret_key"])
        raw_account = client.get_account()
        raw_positions = client.get_positions()
        open_orders = client.get_orders(status="open")
        network_used = True

    current_account = normalize_account(raw_account) if raw_account else {}
    current_positions = [normalize_position(item) for item in raw_positions]

    previous = {"account": {}, "positions": []}
    snapshot_path = root / SNAPSHOT
    if snapshot_path.exists():
        try:
            previous = read_json(snapshot_path)
        except Exception:
            previous = {"account": {}, "positions": []}

    account_tolerance = Decimal(str(policy.get("account_drift_tolerance", "1.00")))
    position_tolerance = Decimal(str(policy.get("position_qty_tolerance", "0.000001")))

    account_drifts = (
        compare_accounts(previous.get("account", {}), current_account, account_tolerance)
        if current_account and previous.get("account")
        else []
    )
    position_drifts = compare_positions(
        previous.get("positions", []),
        current_positions,
        position_tolerance,
    )

    if current_account:
        health = classify(
            current_account,
            account_drifts,
            position_drifts,
            open_orders,
            policy,
        )
    else:
        health = {
            "health": "BLOCKED",
            "issues": blocking_reasons[:],
            "recovery_required": False,
        }

    recovery_plan = build_plan(health, account_drifts, position_drifts)

    state = (
        "PORTFOLIO_SYNC_ACTIVE"
        if network_used and health["health"] == "HEALTHY"
        else "PORTFOLIO_SYNC_RECOVERY_REQUIRED"
        if network_used
        else "PORTFOLIO_SYNC_READY_BLOCKED"
    )

    now = datetime.now(timezone.utc).isoformat()
    result = {
        "stage": "V390.64",
        "state": state,
        "status": "PASS",
        "observed_at": now,
        "network_used": network_used,
        "allow_network": allow_network,
        "blocking_reasons": blocking_reasons,
        "account": current_account,
        "positions": current_positions,
        "open_orders": open_orders,
        "account_drifts": account_drifts,
        "position_drifts": position_drifts,
        "portfolio_health": health,
        "recovery_plan": recovery_plan,
        "read_only": True,
        "paper_endpoint_only": True,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "automatic_recovery_execution_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V391_01_TO_V400_64_AUTONOMOUS_RISK_GOVERNOR",
    }

    write_json(root / ACTUAL / "latest_portfolio_sync_result.json", result)
    append_jsonl(root / ACTUAL / "portfolio_sync_ledger.jsonl", result)

    for item in account_drifts + position_drifts:
        append_jsonl(root / ACTUAL / "portfolio_drift_ledger.jsonl", {
            "observed_at": now,
            **item,
        })

    if recovery_plan:
        append_jsonl(root / ACTUAL / "recovery_plan_ledger.jsonl", {
            "observed_at": now,
            "health": health,
            "actions": recovery_plan,
        })

    if current_account:
        write_json(snapshot_path, {
            "observed_at": now,
            "account": current_account,
            "positions": current_positions,
        })

    return result
