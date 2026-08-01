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
        / "release" / "v121_00" / "output"
        / "actual_autonomous_paper_read_fixture_result.json"
    ).read_text(encoding="utf-8"))

    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "ACTUAL_AUTONOMOUS_PAPER_READ_SESSION",
        "fixture_mode": result["validation_mode"] == "OFFLINE_FIXTURE",
        "paper_url": result["paper_base_url"] == "https://paper-api.alpaca.markets",
        "account_active": result["account_status"] == "ACTIVE",
        "account_redacted": "*" in result["account_id_redacted"],
        "not_blocked": result["trading_blocked"] is False,
        "market_open": result["market_is_open"] is True,
        "positions_one": result["position_count"] == 1,
        "open_orders_one": result["open_order_count"] == 1,
        "closed_orders_two": result["closed_order_count"] == 2,
        "symbols_aapl": result["symbols_held"] == ["AAPL"],
        "five_gets": result["request_methods"] == ["GET"] * 5,
        "read_requests_five": result["read_request_count"] == 5,
        "write_zero": result["write_request_count"] == 0,
        "paper_orders_zero": result["actual_paper_orders_submitted"] == 0,
        "live_zero": result["live_orders_submitted"] == 0,
        "autonomous_ready": result["autonomous_read_ready"] is True,
        "actual_credentials_false": result["actual_credentials_used"] is False,
        "actual_network_false": result["actual_external_network_used"] is False,
        "cash_1000": Decimal(result["cash"]) == Decimal("1000"),
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V120.01-V121.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
