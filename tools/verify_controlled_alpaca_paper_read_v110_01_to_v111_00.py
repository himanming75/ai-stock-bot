from pathlib import Path
import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    result = json.loads((
        Path(args.repository_root).resolve()
        / "release" / "v111_00" / "output"
        / "controlled_alpaca_paper_read_fixture_result.json"
    ).read_text(encoding="utf-8"))

    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "CONTROLLED_ALPACA_PAPER_READ_VALIDATION",
        "fixture_mode": result["validation_mode"] == "OFFLINE_FIXTURE",
        "paper_url": result["paper_base_url"] == "https://paper-api.alpaca.markets",
        "account_active": result["account_status"] == "ACTIVE",
        "account_redacted": "*" in result["account_id_redacted"],
        "positions_one": result["position_count"] == 1,
        "open_orders_one": result["open_order_count"] == 1,
        "closed_orders_one": result["closed_order_count"] == 1,
        "five_read_requests": result["network_requests_executed"] == 5,
        "get_only": result["request_methods"] == ["GET"] * 5,
        "write_zero": result["write_requests_executed"] == 0,
        "paper_orders_zero": result["actual_paper_orders_submitted"] == 0,
        "live_orders_zero": result["live_orders_submitted"] == 0,
        "actual_credentials_false": result["actual_credentials_used"] is False,
        "actual_network_false": result["actual_network_used"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V110.01-V111.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
