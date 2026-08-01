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
        / "release" / "v112_00" / "output"
        / "controlled_alpaca_paper_order_fixture_result.json"
    ).read_text(encoding="utf-8"))
    preview = result["preview"]
    submission = result["submission"]

    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "CONTROLLED_ALPACA_PAPER_SINGLE_ORDER_OPT_IN",
        "fixture_mode": result["validation_mode"] == "OFFLINE_FIXTURE",
        "preview_not_submitted": preview["submitted"] is False,
        "preview_network_zero": preview["network_requests_executed"] == 0,
        "submission_true": submission["submitted"] is True,
        "paper_order_one_fixture": submission["actual_paper_orders_submitted"] == 1,
        "quantity_one": Decimal(submission["quantity"]) == Decimal("1"),
        "notional_50": Decimal(submission["estimated_notional"]) == Decimal("50"),
        "five_requests": submission["network_requests_executed"] == 5,
        "one_write": submission["write_requests_executed"] == 1,
        "method_sequence": result["request_methods"] == ["GET", "GET", "GET", "GET", "POST"],
        "live_zero": submission["live_orders_submitted"] == 0,
        "actual_credentials_false": result["actual_credentials_used"] is False,
        "actual_network_false": result["actual_network_used"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V111.01-V112.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
