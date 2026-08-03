import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = (
    root / "release/v83_49_to_v83_52/actual/"
    "supervised_reentry_runner_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND: " + str(path))

result = json.loads(path.read_text(encoding="utf-8"))
safe_states = {
    "SUPERVISED_REENTRY_RUNNER_WAIT_PLAN",
    "SUPERVISED_REENTRY_RUNNER_DRY_RUN_READY",
    "SUPERVISED_REENTRY_RUNNER_DRY_RUN_COMPLETE",
    "SUPERVISED_REENTRY_RUNNER_COMPLETED",
    "SUPERVISED_REENTRY_RUNNER_LOCK_CLEARED",
}
checks = {
    "stage_range": result.get("stage_range") == "V83.49-V83.52",
    "status": result.get("status") == "PASS",
    "state": result.get("state") in safe_states,
    "paper_only": result.get("paper_only") is True,
    "automatic_execution_disabled": (
        result.get("automatic_execution_enabled") is False
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
    "verification_stage": "V83.52",
    "verification_status": "PASS" if not failed else "FAIL",
    "source_state": result.get("state"),
    "checks": checks,
    "failed": failed,
}, indent=2, sort_keys=True))
raise SystemExit(1 if failed else 0)
