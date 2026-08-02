from pathlib import Path
import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    result = json.loads((
        Path(args.repository_root).resolve()
        / "release/v129_00/output"
        / "order_lifecycle_fill_reconciliation_result.json"
    ).read_text(encoding="utf-8"))

    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "ACTUAL_ORDER_LIFECYCLE_FILL_RECONCILIATION_GATE",
        "waiting_active": result["state"] == "WAITING_ACTIVE_ORDER",
        "terminal_false": result["terminal"] is False,
        "new_order_blocked": result["new_order_allowed"] is False,
        "safe_mode_false": result["safe_mode_engaged"] is False,
        "active_guard": result["active_order_guard_verified"] is True,
        "filled_zero": result["filled_quantity"] == "0",
        "remaining_one": result["remaining_quantity"] == "1",
        "issues_zero": result["issue_count"] == 0,
        "write_zero": result["write_requests_executed"] == 0,
        "paper_zero": result["actual_paper_orders_submitted"] == 0,
        "live_zero": result["live_orders_submitted"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V128.01-V129.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
