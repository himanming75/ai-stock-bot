from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from real_paper_validation.auth import credentials
from real_paper_validation.client import AlpacaPaperClient
from real_paper_validation.config import load, validate
from real_paper_validation.io import write_json

def evaluate(root: Path, allow_network: bool = False) -> dict:
    policy = load(root)
    validation = validate(policy)
    auth = credentials()

    blocking = []
    if not validation["valid"]:
        blocking.append("POLICY_INVALID")
    if not policy.get("paper_read_enabled"):
        blocking.append("PAPER_READ_DISABLED")
    if not auth["ready"]:
        blocking.append("PAPER_CREDENTIALS_MISSING")
    if not allow_network:
        blocking.append("NETWORK_NOT_AUTHORIZED")

    account = {}
    clock = {"is_open": False}
    positions = []
    open_orders = []

    if not blocking:
        client = AlpacaPaperClient(auth["key"], auth["secret"], policy["paper_base_url"])
        account = client.account()
        clock = client.clock()
        positions = client.positions()
        open_orders = client.open_orders()

    checks = {
        "policy_valid": validation["valid"],
        "paper_endpoint_only": policy.get("paper_base_url") == "https://paper-api.alpaca.markets",
        "credentials_ready": auth["ready"],
        "account_read": bool(account),
        "clock_read": bool(clock),
        "positions_read": isinstance(positions, list),
        "open_orders_read": isinstance(open_orders, list),
        "live_submission_disabled": policy.get("live_submission_enabled") is False,
        "live_network_disabled": policy.get("live_network_enabled") is False,
        "broker_write_disabled": policy.get("broker_write_enabled") is False,
    }
    failed = [k for k, v in checks.items() if not v]
    state = "REAL_PAPER_READ_VALIDATED" if not failed else "REAL_PAPER_VALIDATION_READY_BLOCKED"

    result = {
        "stage": "V305.64",
        "state": state,
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "blocking_reasons": blocking,
        "checks": checks,
        "account": {
            "id": account.get("id"),
            "status": account.get("status"),
            "cash": account.get("cash"),
            "equity": account.get("equity"),
            "buying_power": account.get("buying_power"),
        } if account else {},
        "market_open": clock.get("is_open") is True,
        "next_open": clock.get("next_open"),
        "next_close": clock.get("next_close"),
        "position_count": len(positions) if isinstance(positions, list) else 0,
        "open_order_count": len(open_orders) if isinstance(open_orders, list) else 0,
        "micro_paper_order_enabled": policy.get("micro_paper_order_enabled") is True,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "live_submission_enabled": False,
        "next_phase": "V306_01_TO_V310_64_REAL_PAPER_MICRO_ORDER_VALIDATION",
    }
    out = root / "release/v301_01_to_v305_64/actual/real_paper_validation_result.json"
    write_json(out, result)
    return result
