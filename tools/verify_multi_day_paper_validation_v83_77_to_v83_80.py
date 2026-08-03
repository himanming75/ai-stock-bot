import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = (
        root / "release/v83_77_to_v83_80/actual/"
        "multi_day_paper_validation_result.json"
    )
    if not path.exists():
        print(f"RESULT NOT FOUND: {path}")
        return 1
    result = json.loads(path.read_text(encoding="utf-8"))
    checks = {
        "stage_range": result.get("stage_range") == "V83.77-V83.80",
        "status": result.get("status") == "PASS",
        "paper_only": result.get("paper_only") is True,
        "broker_write_disabled": result.get("broker_write_enabled") is False,
        "order_submission_disabled": (
            result.get("order_submission_enabled") is False
        ),
        "live_trading_disabled": result.get("live_trading_enabled") is False,
        "external_network_disabled": (
            result.get("external_network_enabled") is False
        ),
        "continuous_loop_disabled": (
            result.get("continuous_loop_enabled") is False
        ),
        "windows_task_disabled": result.get("windows_task_enabled") is False,
        "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
        "live_orders_zero": result.get("live_orders_submitted") == 0,
        "network_requests_zero": result.get("network_requests_executed") == 0,
        "write_requests_zero": result.get("write_requests_executed") == 0,
        "blocking_issues_zero": result.get("blocking_issue_count") == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    payload = {
        "verification_stage": "V83.80",
        "verification_status": "PASS" if not failed else "FAIL",
        "source_state": result.get("state", ""),
        "completed_days": result.get("completed_days", 0),
        "requirement_met": result.get("requirement_met", False),
        "checks": checks,
        "failed": failed,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
