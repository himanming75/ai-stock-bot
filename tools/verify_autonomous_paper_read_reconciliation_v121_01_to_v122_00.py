from pathlib import Path
import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    result = json.loads((
        Path(args.repository_root).resolve()
        / "release" / "v122_00" / "output"
        / "autonomous_paper_read_reconciliation_result.json"
    ).read_text(encoding="utf-8"))

    issue_codes = [item["code"] for item in result["issues"]]
    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "AUTONOMOUS_PAPER_READ_RECONCILIATION",
        "safe_mode_true": result["safe_mode_engaged"] is True,
        "order_not_allowed": result["autonomous_order_allowed"] is False,
        "reconciliation_safe_mode": result["reconciliation_status"] == "SAFE_MODE",
        "open_order_guard": result["open_order_guard_verified"] is True,
        "open_order_issue": "OPEN_ORDER_COUNT_MISMATCH" in issue_codes,
        "blocking_positive": result["blocking_issue_count"] >= 1,
        "cash_match": result["cash_matched"] is True,
        "equity_match": result["equity_matched"] is True,
        "position_count_match": result["position_count_matched"] is True,
        "position_symbols_match": result["position_symbols_matched"] is True,
        "recovery_match": result["recovery_generation_matched"] is True,
        "runtime_state_match": result["runtime_state_matched"] is True,
        "network_zero": result["network_requests_executed"] == 0,
        "write_zero": result["write_requests_executed"] == 0,
        "paper_orders_zero": result["actual_paper_orders_submitted"] == 0,
        "live_zero": result["live_orders_submitted"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V121.01-V122.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
