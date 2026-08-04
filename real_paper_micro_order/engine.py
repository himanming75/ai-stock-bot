from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from real_paper_micro_order.auth import credentials
from real_paper_micro_order.client import AlpacaPaperClient
from real_paper_micro_order.config import load, validate
from real_paper_micro_order.idempotency import (
    already_submitted,
    client_order_id,
    record,
)
from real_paper_micro_order.io import write_json
from real_paper_micro_order.token import consume, inspect

def evaluate(
    root: Path,
    allow_network: bool = False,
    allow_submission: bool = False,
) -> dict:
    policy = load(root)
    validation = validate(policy)
    auth = credentials()
    token = inspect(root, policy["confirmation_phrase"])
    client_id = client_order_id(root, policy)
    duplicate = already_submitted(root, client_id)

    blocking = []
    if not validation["valid"]:
        blocking.append("POLICY_INVALID")
    if not policy.get("micro_order_enabled"):
        blocking.append("MICRO_ORDER_DISABLED")
    if not auth["ready"]:
        blocking.append("PAPER_CREDENTIALS_MISSING")
    if not token["valid"]:
        blocking.append("ONE_TIME_TOKEN_INVALID")
    if duplicate:
        blocking.append("MICRO_ORDER_ALREADY_SUBMITTED")
    if not allow_network:
        blocking.append("NETWORK_NOT_AUTHORIZED")
    if not allow_submission:
        blocking.append("SUBMISSION_NOT_AUTHORIZED")

    account = {}
    clock = {"is_open": False}
    open_orders = []
    asset = {}
    receipt = {}
    observed_order = {}

    client = None
    if allow_network and auth["ready"]:
        client = AlpacaPaperClient(auth["key"], auth["secret"], policy["paper_base_url"])
        account = client.account()
        clock = client.clock()
        open_orders = client.open_orders()
        asset = client.asset(str(policy["symbol"]).upper())

    market_open = clock.get("is_open") is True
    if policy.get("require_market_open") and not market_open:
        blocking.append("MARKET_CLOSED")
    if policy.get("require_no_open_orders") and open_orders:
        blocking.append("OPEN_ORDER_ALREADY_PRESENT")
    if asset and not asset.get("tradable"):
        blocking.append("ASSET_NOT_TRADABLE")
    if asset and not asset.get("fractionable"):
        blocking.append("ASSET_NOT_FRACTIONABLE")
    if account and str(account.get("status")) != "ACTIVE":
        blocking.append("ACCOUNT_NOT_ACTIVE")

    blocking = sorted(set(blocking))
    submission_allowed = (
        allow_network
        and allow_submission
        and not blocking
        and client is not None
    )

    if submission_allowed:
        payload = {
            "symbol": str(policy["symbol"]).upper(),
            "notional": f"{float(policy['notional']):.2f}",
            "side": str(policy["side"]).lower(),
            "type": "market",
            "time_in_force": "day",
            "client_order_id": client_id,
        }
        receipt = client.submit_order(payload)
        record(root, client_id, receipt)
        consume(root, client_id)
        observed_order = client.order_by_client_id(client_id)

    actual_paper_orders = 1 if receipt else 0
    state = (
        "REAL_PAPER_MICRO_ORDER_SUBMITTED"
        if receipt
        else "REAL_PAPER_MICRO_ORDER_READY_BLOCKED"
    )
    result = {
        "stage": "V310.64",
        "state": state,
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "blocking_reasons": blocking,
        "client_order_id": client_id,
        "duplicate": duplicate,
        "account_status": account.get("status"),
        "market_open": market_open,
        "open_order_count_before": len(open_orders),
        "asset": {
            "symbol": asset.get("symbol"),
            "tradable": asset.get("tradable"),
            "fractionable": asset.get("fractionable"),
            "status": asset.get("status"),
        } if asset else {},
        "requested_order": {
            "symbol": str(policy["symbol"]).upper(),
            "side": str(policy["side"]).lower(),
            "notional": float(policy["notional"]),
            "type": "market",
            "time_in_force": "day",
        },
        "receipt": receipt,
        "observed_order": observed_order,
        "actual_paper_orders_submitted": actual_paper_orders,
        "actual_live_orders_submitted": 0,
        "live_submission_enabled": False,
        "live_network_enabled": False,
        "broker_write_enabled": False,
        "next_phase": "V311_01_TO_V320_64_REAL_PAPER_AUTONOMOUS_DATA_COLLECTION",
    }
    write_json(
        root / "release/v306_01_to_v310_64/actual/real_paper_micro_order_result.json",
        result,
    )
    return result
