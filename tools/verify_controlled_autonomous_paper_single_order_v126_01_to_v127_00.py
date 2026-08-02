from pathlib import Path
import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    result = json.loads((
        Path(args.repository_root).resolve()
        / "release/v127_00/output/controlled_autonomous_paper_single_order_result.json"
    ).read_text(encoding="utf-8"))

    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "CONTROLLED_AUTONOMOUS_PAPER_SINGLE_ORDER",
        "existing_order_wait": result["decision"] == "EXISTING_ORDER_WAIT",
        "existing_one": result["existing_open_order_count"] == 1,
        "guard_verified": result["existing_order_guard_verified"] is True,
        "readiness_verified": result["readiness_verified"] is True,
        "account_verified": result["account_verified"] is True,
        "market_verified": result["market_open_verified"] is True,
        "paper_zero": result["actual_paper_orders_submitted"] == 0,
        "write_zero": result["write_requests_executed"] == 0,
        "live_zero": result["live_orders_submitted"] == 0,
        "live_disabled": result["live_trading_enabled"] is False,
    }
    failed = [name for name, ok in checks.items() if not ok]
    output = {
        "stage_range": "V126.01-V127.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
