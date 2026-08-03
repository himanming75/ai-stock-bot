import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = (
        root / "release/v88_09_to_v88_16/actual/"
        "paper_orchestrator_result.json"
    )
    if not path.exists():
        print(f"RESULT NOT FOUND: {path}")
        return 1

    result = json.loads(path.read_text(encoding="utf-8"))
    checks = {
        "stage_range": result.get("stage_range") == "V88.09-V88.16",
        "status_pass": result.get("status") == "PASS",
        "state_ready": (
            result.get("state") == "PAPER_AUTOMATION_ORCHESTRATOR_READY"
        ),
        "all_steps_completed": (
            result.get("completed_step_count") == result.get("total_step_count")
            == 7
        ),
        "safe_mode_disabled": result.get("safe_mode") is False,
        "checkpoint_exists": Path(
            result.get("checkpoint_path", "")
        ).exists(),
        "ledger_exists": Path(result.get("ledger_path", "")).exists(),
        "daily_report_exists": Path(
            result.get("daily_report_path", "")
        ).exists(),
        "paper_only": result.get("paper_only") is True,
        "continuous_loop_disabled": (
            result.get("continuous_loop_enabled") is False
        ),
        "windows_task_disabled": (
            result.get("windows_task_enabled") is False
        ),
        "broker_write_disabled": (
            result.get("broker_write_enabled") is False
        ),
        "order_submission_disabled": (
            result.get("order_submission_enabled") is False
        ),
        "live_trading_disabled": (
            result.get("live_trading_enabled") is False
        ),
        "external_network_disabled": (
            result.get("external_network_enabled") is False
        ),
        "paper_orders_zero": (
            result.get("actual_paper_orders_submitted") == 0
        ),
        "live_orders_zero": result.get("live_orders_submitted") == 0,
        "network_requests_zero": (
            result.get("network_requests_executed") == 0
        ),
        "write_requests_zero": (
            result.get("write_requests_executed") == 0
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    payload = {
        "verification_stage": "V88.16",
        "verification_status": "PASS" if not failed else "FAIL",
        "state": result.get("state"),
        "completed_step_count": result.get("completed_step_count"),
        "total_step_count": result.get("total_step_count"),
        "safe_mode": result.get("safe_mode"),
        "checks": checks,
        "failed": failed,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
