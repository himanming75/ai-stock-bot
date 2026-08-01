from pathlib import Path
import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    result = json.loads((
        Path(args.repository_root).resolve()
        / "release" / "v115_00" / "output"
        / "alpaca_paper_session_scheduler_result.json"
    ).read_text(encoding="utf-8"))

    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "ALPACA_PAPER_SESSION_SCHEDULER_FOUNDATION",
        "action_sequence": result["actions"] == [
            "PREPARE", "START_SESSION", "RUN_CYCLE", "RECOVER_SESSION", "CLOSE_SESSION"
        ],
        "phase_sequence": result["phases"] == [
            "PRE_MARKET", "REGULAR", "REGULAR", "REGULAR", "AFTER_HOURS"
        ],
        "cycle_one": result["cycle_count"] == 1,
        "heartbeat_four": result["heartbeat_count"] == 4,
        "restart_one": result["restart_count"] == 1,
        "prepared": result["session_prepared"] is True,
        "inactive": result["session_active"] is False,
        "closed": result["session_closed"] is True,
        "state_exists": result["persisted_state_exists"] is True,
        "network_zero": result["network_requests_executed"] == 0,
        "write_zero": result["write_requests_executed"] == 0,
        "paper_orders_zero": result["actual_paper_orders_submitted"] == 0,
        "live_zero": result["live_orders_submitted"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V114.01-V115.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
