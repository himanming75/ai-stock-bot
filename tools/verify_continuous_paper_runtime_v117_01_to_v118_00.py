from pathlib import Path
import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    result = json.loads((
        Path(args.repository_root).resolve()
        / "release" / "v118_00" / "output"
        / "continuous_paper_runtime_release_candidate_result.json"
    ).read_text(encoding="utf-8"))

    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "CONTINUOUS_PAPER_RUNTIME_RELEASE_CANDIDATE",
        "rc1": result["release_candidate"] == "CONTINUOUS_PAPER_RUNTIME_RC1",
        "started": result["start_action"] == "STARTED",
        "first_stopped": result["first_stop_action"] == "STOPPED",
        "restarted": result["restart_action"] == "RECOVERED",
        "final_stopped": result["final_stop_action"] == "STOPPED",
        "runtime_stopped": result["runtime_final_state"] == "STOPPED",
        "ticks_109": result["ticks_started"] == 109,
        "ticks_completed_109": result["ticks_completed"] == 109,
        "scheduler_decisions_110": result["scheduler_decisions"] == 110,
        "cycles_105": result["cycles_completed"] == 105,
        "requested_105": result["cycles_requested"] == 105,
        "heartbeats_109": result["heartbeat_calls"] == 109,
        "watchdogs_109": result["watchdog_checks"] == 109,
        "recovery_one": result["recoveries_completed"] == 1,
        "stop_requests_two": result["stop_requests"] == 2,
        "shutdowns_two": result["graceful_shutdowns"] == 2,
        "failures_zero": result["failures"] == 0,
        "prepare_one": result["integration_prepare_count"] == 1,
        "start_one": result["integration_start_count"] == 1,
        "integration_cycles_105": result["integration_cycle_count"] == 105,
        "integration_recover_two": result["integration_recover_count"] == 2,
        "close_one": result["integration_close_count"] == 1,
        "stability_cycles_105": result["stability_cycle_count"] == 105,
        "stability_recovery_one": result["stability_recovery_count"] == 1,
        "stability_shutdown_two": result["stability_shutdown_count"] == 2,
        "network_zero": result["network_requests_executed"] == 0,
        "write_zero": result["write_requests_executed"] == 0,
        "paper_orders_zero": result["actual_paper_orders_submitted"] == 0,
        "live_zero": result["live_orders_submitted"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V117.01-V118.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
