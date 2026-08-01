from pathlib import Path
import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    path = Path(args.repository_root).resolve() / "release" / "v102_00" / "output" / "runtime_foundation_result.json"
    result = json.loads(path.read_text(encoding="utf-8"))
    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "REAL_RUNTIME_FOUNDATION",
        "runtime_stopped": result["runtime_state"] == "STOPPED",
        "ticks_three": result["tick_count"] == 3,
        "recovery_exists": result["recovery_snapshot_exists"] is True,
        "network_write_disabled": result["network_write_enabled"] is False,
        "paper_submit_disabled": result["paper_order_submission_enabled"] is False,
        "live_disabled": result["live_trading_enabled"] is False,
        "network_zero": result["network_requests_executed"] == 0,
        "orders_zero": result["actual_orders_submitted"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V101.01-V102.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
