import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = (
    root / "release/v83_33_to_v83_36/actual/"
    "trigger_recovery_dispatch_chain_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND: " + str(path))

result = json.loads(path.read_text(encoding="utf-8"))
safe_states = {
    "TRIGGER_CHAIN_WAIT_TRIGGER",
    "TRIGGER_CHAIN_TRIGGER_PENDING",
    "TRIGGER_CHAIN_DISPATCH_READY",
    "TRIGGER_CHAIN_DISPATCH_RUNNING",
    "TRIGGER_CHAIN_COMPLETED",
    "TRIGGER_CHAIN_RECOVERY_REQUIRED",
    "TRIGGER_RECOVERY_LOCK_CLEARED",
}
checks = {
    "stage_range": result.get("stage_range") == "V83.33-V83.36",
    "status": result.get("status") == "PASS",
    "state": result.get("state") in safe_states,
    "paper_only": result.get("paper_only") is True,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "order_submission_disabled": (
        result.get("order_submission_enabled") is False
    ),
    "live_trading_disabled": result.get("live_trading_enabled") is False,
    "external_network_unused": (
        result.get("actual_external_network_used") is False
    ),
    "network_requests_zero": result.get("network_requests_executed") == 0,
    "write_requests_zero": result.get("write_requests_executed") == 0,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("live_orders_submitted") == 0,
}
failed = [name for name, passed in checks.items() if not passed]
print(json.dumps({
    "verification_stage": "V83.36",
    "verification_status": "PASS" if not failed else "FAIL",
    "source_state": result.get("state"),
    "checks": checks,
    "failed": failed,
}, indent=2, sort_keys=True))
raise SystemExit(1 if failed else 0)
