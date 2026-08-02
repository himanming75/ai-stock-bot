from pathlib import Path
import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    result = json.loads((
        Path(args.repository_root).resolve()
        / "release/v130_00/output"
        / "existing_paper_order_lifecycle_monitor_result.json"
    ).read_text(encoding="utf-8"))

    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "EXISTING_PAPER_ORDER_LIFECYCLE_MONITORING_RUNTIME",
        "continue_tracking": result["decision"] == "CONTINUE_TRACKING",
        "three_polls": result["poll_count"] == 3,
        "two_transitions": result["transition_count"] == 2,
        "material_zero": result["material_transition_count"] == 0,
        "accepted_final": result["final_status"] == "ACCEPTED",
        "filled_zero": result["final_filled_quantity"] == "0",
        "remaining_one": result["final_remaining_quantity"] == "1",
        "new_order_blocked": result["new_order_allowed"] is False,
        "safe_mode_false": result["safe_mode_engaged"] is False,
        "guard_verified": result["active_order_guard_verified"] is True,
        "network_zero": result["network_requests_executed"] == 0,
        "write_zero": result["write_requests_executed"] == 0,
        "paper_zero": result["actual_paper_orders_submitted"] == 0,
        "live_zero": result["live_orders_submitted"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V129.01-V130.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
