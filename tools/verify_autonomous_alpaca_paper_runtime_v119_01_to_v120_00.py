from pathlib import Path
import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    result = json.loads((
        Path(args.repository_root).resolve()
        / "release" / "v120_00" / "output"
        / "autonomous_alpaca_paper_runtime_foundation_result.json"
    ).read_text(encoding="utf-8"))

    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "AUTONOMOUS_ALPACA_PAPER_RUNTIME_FOUNDATION",
        "fixture_preview": result["mode"] == "OFFLINE_FIXTURE_PREVIEW_ONLY",
        "preview_decision": result["decision"] == "PREVIEW_ORDER",
        "symbol_aapl": result["symbol"] == "AAPL",
        "quantity_one": result["quantity"] == 1,
        "notional_50": result["estimated_notional"] == 50.0,
        "read_requests_two": result["read_requests_executed"] == 2,
        "write_zero": result["write_requests_executed"] == 0,
        "paper_orders_zero": result["actual_paper_orders_submitted"] == 0,
        "live_zero": result["live_orders_submitted"] == 0,
        "runtime_stopped": result["runtime_final_state"] == "STOPPED",
        "single_order_limit": result["single_order_limit"] == 1,
        "max_notional_100": result["max_order_notional"] == 100.0,
        "live_disabled": result["live_trading_enabled"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V119.01-V120.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
