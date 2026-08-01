from pathlib import Path
from decimal import Decimal
import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    result = json.loads((
        Path(args.repository_root).resolve()
        / "release" / "v113_00" / "output"
        / "actual_alpaca_paper_order_validation_fixture_result.json"
    ).read_text(encoding="utf-8"))

    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "ACTUAL_ALPACA_PAPER_ORDER_VALIDATION",
        "fixture_mode": result["validation_mode"] == "OFFLINE_FIXTURE",
        "filled": result["final_status"] == "filled",
        "terminal": result["terminal_status_reached"] is True,
        "polls_three": result["poll_attempts"] == 3,
        "requested_one": Decimal(result["requested_quantity"]) == Decimal("1"),
        "filled_one": Decimal(result["filled_quantity"]) == Decimal("1"),
        "position_one": Decimal(result["position_quantity"]) == Decimal("1"),
        "account_active": result["account_status"] == "ACTIVE",
        "not_blocked": result["trading_blocked"] is False,
        "five_gets": result["request_methods"] == ["GET"] * 5,
        "network_five": result["network_requests_executed"] == 5,
        "write_zero": result["write_requests_executed"] == 0,
        "additional_orders_zero": result["additional_orders_submitted"] == 0,
        "live_zero": result["live_orders_submitted"] == 0,
        "actual_credentials_false": result["actual_credentials_used"] is False,
        "actual_network_false": result["actual_external_network_used"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V112.01-V113.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
