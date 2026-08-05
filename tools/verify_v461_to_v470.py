from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT
        / "release/v470_64/actual/alpaca_paper_read_safety_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": result.get("stage") == "V470.64",
    "status": result.get("status") == "PASS",
    "state": result.get("state") == "ALPACA_PAPER_READ_SAFETY_READY",
    "snapshot_valid": result.get("integrity", {}).get("valid") is True,
    "snapshot_hash": len(
        str(result.get("integrity", {}).get("snapshot_hash", ""))
    ) == 64,
    "account_read": result.get("account_read_completed") is True,
    "positions_read": result.get("positions_read_completed") is True,
    "orders_read": result.get("open_orders_read_completed") is True,
    "clock_read": result.get("market_clock_read_completed") is True,
    "tradability_read": (
        result.get("asset_tradability_read_completed") is True
    ),
    "read_only": result.get("read_only_http_enforced") is True,
    "paper_endpoint": result.get("paper_endpoint_enforced") is True,
    "timeout_retry": result.get("timeout_retry_enabled") is True,
    "rate_limit": result.get("rate_limit_handling_enabled") is True,
    "network_recovery": result.get("network_recovery_enabled") is True,
    "broker_write_off": result.get("broker_write_enabled") is False,
    "paper_submission_off": (
        result.get("paper_submission_enabled") is False
    ),
    "live_submission_off": result.get("live_submission_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}

verification = {
    "verification_stage": "V470.64",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
