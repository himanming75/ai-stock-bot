from pathlib import Path
import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    result = json.loads((
        Path(args.repository_root).resolve()
        / "release" / "v123_00" / "output"
        / "autonomous_paper_order_identity_reconciliation_result.json"
    ).read_text(encoding="utf-8"))

    record = result["records"][0]
    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "AUTONOMOUS_PAPER_ORDER_IDENTITY_RECONCILIATION",
        "fixture_mode": result["validation_mode"] == "OFFLINE_FIXTURE_EXTERNAL_ORDER",
        "identity_safe_mode": result["identity_status"] == "SAFE_MODE",
        "safe_mode_true": result["safe_mode_engaged"] is True,
        "order_not_allowed": result["autonomous_order_allowed"] is False,
        "open_order_one": result["open_order_count"] == 1,
        "external_one": result["external_order_count"] == 1,
        "bot_zero": result["bot_order_count"] == 0,
        "unknown_zero": result["unknown_order_count"] == 0,
        "recognized_zero": result["recognized_internal_order_count"] == 0,
        "blocking_one": result["blocking_order_count"] == 1,
        "ownership_external": record["ownership"] == "EXTERNAL",
        "symbol_aapl": record["symbol"] == "AAPL",
        "side_buy": record["side"] == "BUY",
        "quantity_one": record["quantity"] == "1",
        "external_guard": result["external_order_guard_verified"] is True,
        "network_zero": result["read_requests_executed"] == 0,
        "write_zero": result["write_requests_executed"] == 0,
        "paper_orders_zero": result["actual_paper_orders_submitted"] == 0,
        "live_zero": result["live_orders_submitted"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V122.01-V123.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
