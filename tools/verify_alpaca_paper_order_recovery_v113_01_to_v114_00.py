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
        / "release" / "v114_00" / "output"
        / "alpaca_paper_order_recovery_fixture_result.json"
    ).read_text(encoding="utf-8"))

    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "ALPACA_PAPER_ORDER_RECOVERY_RESTART",
        "fixture_mode": result["validation_mode"] == "OFFLINE_FIXTURE",
        "checkpoint_partial": result["checkpoint_status"] == "partially_filled",
        "checkpoint_half": Decimal(result["checkpoint_filled_quantity"]) == Decimal("0.5"),
        "recovered_filled": result["recovered_status"] == "filled",
        "recovered_one": Decimal(result["recovered_filled_quantity"]) == Decimal("1"),
        "terminal": result["terminal"] is True,
        "generation_one": result["recovery_generation"] == 1,
        "persisted_filled": result["persisted_status"] == "filled",
        "persisted_generation_one": result["persisted_generation"] == 1,
        "duplicate_prevented": result["duplicate_submission_prevented"] is True,
        "read_only": result["restart_read_only"] is True,
        "one_get": result["request_methods"] == ["GET"],
        "network_one": result["network_requests_executed"] == 1,
        "write_zero": result["write_requests_executed"] == 0,
        "additional_orders_zero": result["additional_orders_submitted"] == 0,
        "live_zero": result["live_orders_submitted"] == 0,
        "actual_credentials_false": result["actual_credentials_used"] is False,
        "actual_network_false": result["actual_external_network_used"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V113.01-V114.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
