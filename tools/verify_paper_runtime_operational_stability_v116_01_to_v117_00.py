from pathlib import Path
import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    result = json.loads((
        Path(args.repository_root).resolve()
        / "release" / "v117_00" / "output"
        / "paper_runtime_operational_stability_result.json"
    ).read_text(encoding="utf-8"))
    stats = result["stability_stats"]

    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "PAPER_RUNTIME_OPERATIONAL_STABILITY",
        "long_run_500": result["successful_long_run_cycles"] == 500,
        "runtime_cycles_500": result["runtime_cycle_count"] == 500,
        "heartbeats_500": result["heartbeat_count"] == 500,
        "failure_sequence": result["failure_actions"] == [
            "CYCLE_FAILED", "CYCLE_FAILED", "CIRCUIT_OPEN"
        ],
        "backoff_sequence": result["backoff_sequence"] == [5, 15],
        "circuit_open": result["circuit_open_after_failures"] is True,
        "recovered": result["recovery_action"] == "RECOVERED",
        "shutdown": result["shutdown_action"] == "SHUTDOWN",
        "runtime_stopped": result["runtime_final_state"] == "STOPPED",
        "cycles_attempted_503": stats["cycles_attempted"] == 503,
        "cycles_completed_500": stats["cycles_completed"] == 500,
        "failures_three": stats["cycle_failures"] == 3,
        "max_failures_three": stats["max_observed_consecutive_failures"] == 3,
        "recovery_success_one": stats["recoveries_succeeded"] == 1,
        "shutdown_one": stats["graceful_shutdowns"] == 1,
        "network_zero": result["network_requests_executed"] == 0,
        "write_zero": result["write_requests_executed"] == 0,
        "paper_orders_zero": result["actual_paper_orders_submitted"] == 0,
        "live_zero": result["live_orders_submitted"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V116.01-V117.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
