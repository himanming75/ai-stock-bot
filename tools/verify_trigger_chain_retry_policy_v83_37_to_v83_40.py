import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = (
    root / "release/v83_37_to_v83_40/actual/"
    "trigger_chain_retry_policy_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND: " + str(path))

result = json.loads(path.read_text(encoding="utf-8"))
safe_states = {
    "TRIGGER_RETRY_POLICY_IDLE",
    "TRIGGER_RETRY_WAIT_FAILURE",
    "TRIGGER_RETRY_READY",
    "TRIGGER_RETRY_PLANNED",
    "TRIGGER_RETRY_IN_PROGRESS",
    "TRIGGER_RETRY_COMPLETED",
    "TRIGGER_RETRY_NOT_ELIGIBLE",
    "TRIGGER_RETRY_BUDGET_EXHAUSTED",
    "TRIGGER_RETRY_LOCK_CLEARED",
    "NO_ACTIVE_TRIGGER_RETRY",
}
checks = {
    "stage_range": result.get("stage_range") == "V83.37-V83.40",
    "status": result.get("status") == "PASS",
    "state": result.get("state") in safe_states,
    "paper_only": result.get("paper_only") is True,
    "automatic_retry_disabled": (
        result.get("automatic_retry_execution_enabled") is False
    ),
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
    "verification_stage": "V83.40",
    "verification_status": "PASS" if not failed else "FAIL",
    "source_state": result.get("state"),
    "checks": checks,
    "failed": failed,
}, indent=2, sort_keys=True))
raise SystemExit(1 if failed else 0)
