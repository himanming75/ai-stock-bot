from pathlib import Path
import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    result = json.loads((
        Path(args.repository_root).resolve()
        / "release/v126_00/output/autonomous_safe_mode_recovery_gate_result.json"
    ).read_text(encoding="utf-8"))

    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "AUTONOMOUS_SAFE_MODE_RECOVERY_GATE",
        "read_only_ready": result["state"] == "READ_ONLY_READY",
        "safe_mode_false": result["safe_mode_engaged"] is False,
        "order_not_yet_allowed": result["autonomous_order_allowed"] is False,
        "paper_write_not_ready": result["paper_write_ready"] is False,
        "all_checks_pass": result["all_blocking_checks_passed"] is True,
        "passed_twelve": result["passed_check_count"] == 12,
        "failed_zero": result["failed_check_count"] == 0,
        "blocking_zero": result["blocking_failure_count"] == 0,
        "approval_false": result["approval_token_verified"] is False,
        "write_not_requested": result["write_enablement_requested"] is False,
        "network_zero": result["network_requests_executed"] == 0,
        "write_zero": result["write_requests_executed"] == 0,
        "paper_orders_zero": result["actual_paper_orders_submitted"] == 0,
        "live_zero": result["live_orders_submitted"] == 0,
    }
    failed = [name for name, value in checks.items() if not value]
    output = {
        "stage_range": "V125.01-V126.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
