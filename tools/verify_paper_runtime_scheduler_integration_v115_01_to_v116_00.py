from pathlib import Path
import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    result = json.loads((
        Path(args.repository_root).resolve()
        / "release" / "v116_00" / "output"
        / "paper_runtime_scheduler_integration_result.json"
    ).read_text(encoding="utf-8"))

    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "PAPER_RUNTIME_SCHEDULER_INTEGRATION",
        "scheduler_sequence": result["scheduler_actions"] == [
            "PREPARE", "START_SESSION", "RUN_CYCLE", "RECOVER_SESSION", "CLOSE_SESSION"
        ],
        "integration_sequence": result["integration_events"] == [
            "PREPARED", "SESSION_STARTED", "CYCLE_COMPLETED",
            "SESSION_RECOVERED", "SESSION_CLOSED"
        ],
        "runtime_stopped": result["runtime_final_state"] == "STOPPED",
        "prepare_one": result["prepare_count"] == 1,
        "start_one": result["start_count"] == 1,
        "cycle_one": result["cycle_count"] == 1,
        "recover_one": result["recover_count"] == 1,
        "stop_one": result["stop_count"] == 1,
        "recovery_two": result["recovery_snapshot_count"] == 2,
        "signal_one": result["signal_count"] == 1,
        "risk_one": result["risk_approved_count"] == 1,
        "execution_one": result["execution_accepted_count"] == 1,
        "fill_one": result["fill_completed_count"] == 1,
        "portfolio_one": result["portfolio_update_count"] == 1,
        "network_zero": result["network_requests_executed"] == 0,
        "write_zero": result["write_requests_executed"] == 0,
        "paper_orders_zero": result["actual_paper_orders_submitted"] == 0,
        "live_zero": result["live_orders_submitted"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V115.01-V116.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
