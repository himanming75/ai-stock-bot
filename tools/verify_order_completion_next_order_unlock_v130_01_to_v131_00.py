from pathlib import Path
import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    result = json.loads((
        Path(args.repository_root).resolve()
        / "release/v131_00/output"
        / "order_completion_next_order_unlock_result.json"
    ).read_text(encoding="utf-8"))

    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "ORDER_COMPLETION_NEXT_ORDER_UNLOCK_GATE",
        "active_locked": result["state"] == "LOCKED_ACTIVE_ORDER",
        "completion_false": result["completion_verified"] is False,
        "new_order_blocked": result["new_order_allowed"] is False,
        "safe_mode_false": result["safe_mode_engaged"] is False,
        "terminal_false": result["terminal"] is False,
        "accepted": result["final_status"] == "ACCEPTED",
        "filled_zero": result["filled_quantity"] == "0",
        "remaining_one": result["remaining_quantity"] == "1",
        "ledger_not_written": result["ledger_entry_written"] is False,
        "active_lock_verified": result["active_lock_verified"] is True,
        "network_zero": result["network_requests_executed"] == 0,
        "write_zero": result["write_requests_executed"] == 0,
        "paper_zero": result["actual_paper_orders_submitted"] == 0,
        "live_zero": result["live_orders_submitted"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V130.01-V131.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
