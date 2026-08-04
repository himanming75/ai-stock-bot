import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = (
    ROOT / "release/v106_01_to_v106_32/actual/"
    "daily_paper_runner_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "stage": result.get("stage_range") == "V106.01-V106.32",
    "status": result.get("status") == "PASS",
    "allowed_state": result.get("state") in {
        "DAILY_PAPER_TRADING_RUN_COMPLETED",
        "DAILY_PAPER_TRADING_RUN_NO_ACTION",
        "DAILY_PAPER_TRADING_SOURCE_REQUIRED",
        "DAILY_PAPER_TRADING_PREFLIGHT_BLOCKED",
        "DAILY_PAPER_TRADING_DUPLICATE_RUN_BLOCKED",
    },
    "hash_valid": len(
        result.get("daily_runner_certificate_sha256", "")
    ) == 64,
    "selected_session_valid": isinstance(
        result.get("selected_session", {}), dict
    ),
    "paper_approval_valid": (
        isinstance(result.get("paper_approval", {}), dict)
        if result.get("state") != "DAILY_PAPER_TRADING_DUPLICATE_RUN_BLOCKED"
        else True
    ),
    "live_execution_disabled": (
        result.get("live_execution_authorized") is False
    ),
    "broker_submission_disabled": (
        result.get("broker_submission_authorized") is False
    ),
    "credentials_unused": result.get("actual_credentials_used") is False,
    "network_unused": result.get("actual_external_network_used") is False,
    "orders_zero": result.get("actual_orders_submitted") == 0,
    "paper_only": result.get("paper_only") is True,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "orders_disabled": result.get("order_submission_enabled") is False,
    "live_disabled": result.get("live_trading_enabled") is False,
    "network_disabled": result.get("external_network_enabled") is False,
    "background_service_not_running": (
        result.get("background_service_running") is False
    ),
    "windows_task_disabled": result.get("windows_task_enabled") is False,
}
failed = [name for name, passed in checks.items() if not passed]
print(json.dumps({
    "verification_stage": "V106.32",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": result.get("state"),
    "run_id": result.get("run_id"),
    "selected_session": result.get("selected_session"),
    "preflight": result.get("preflight"),
    "paper_approval": result.get("paper_approval"),
    "daily_plan": result.get("daily_plan"),
    "daily_report": result.get("daily_report"),
    "duplicate": result.get("duplicate"),
    "checkpoint": result.get("checkpoint"),
    "checks": checks,
    "failed": failed,
}, indent=2, sort_keys=True))
raise SystemExit(0 if not failed else 1)
