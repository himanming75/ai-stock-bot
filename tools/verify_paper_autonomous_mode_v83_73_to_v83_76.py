import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = (
    root / "release/v83_73_to_v83_76/actual/"
    "paper_autonomous_mode_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND: " + str(path))

result = json.loads(path.read_text(encoding="utf-8"))
safe_states = {
    "PAPER_AUTONOMOUS_CYCLE_READY",
    "PAPER_AUTONOMOUS_CYCLE_AUTHORIZED",
    "PAPER_AUTONOMOUS_CYCLE_ACTIVE",
    "PAPER_AUTONOMOUS_CYCLE_COMPLETED",
    "PAPER_AUTONOMOUS_LOCK_CLEARED",
    "PAPER_AUTONOMOUS_OPERATOR_ATTENTION_REQUIRED",
    "PAPER_AUTONOMOUS_CERTIFICATION_REQUIRED",
    "PAPER_AUTONOMOUS_RECOVERY_REQUIRED",
    "PAPER_AUTONOMOUS_EXISTING_CYCLE_ACTIVE",
}
checks = {
    "stage_range": result.get("stage_range") == "V83.73-V83.76",
    "status": result.get("status") == "PASS",
    "state": result.get("state") in safe_states,
    "paper_only": result.get("paper_only") is True,
    "single_cycle_only": result.get("single_cycle_only") is True,
    "continuous_loop_disabled": (
        result.get("continuous_loop_enabled") is False
    ),
    "windows_task_disabled": result.get("windows_task_enabled") is False,
    "broker_execution_disabled": (
        result.get("automatic_broker_execution_enabled") is False
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
    "verification_stage": "V83.76",
    "verification_status": "PASS" if not failed else "FAIL",
    "source_state": result.get("state"),
    "checks": checks,
    "failed": failed,
}, indent=2, sort_keys=True))
raise SystemExit(1 if failed else 0)
