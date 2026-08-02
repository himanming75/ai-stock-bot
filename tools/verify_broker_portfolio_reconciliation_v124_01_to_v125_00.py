from pathlib import Path
import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    result = json.loads((
        Path(args.repository_root).resolve()
        / "release/v125_00/output"
        / "broker_portfolio_reconciliation_result.json"
    ).read_text(encoding="utf-8"))

    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "BROKER_PORTFOLIO_RECONCILIATION",
        "reconciliation_matched": result["reconciliation_status"] == "MATCHED",
        "safe_mode_false": result["safe_mode_engaged"] is False,
        "order_allowed": result["autonomous_order_allowed"] is True,
        "cash_match": result["cash_matched"] is True,
        "equity_match": result["equity_matched"] is True,
        "buying_power_match": result["buying_power_matched"] is True,
        "position_count_match": result["position_count_matched"] is True,
        "position_symbols_match": result["position_symbols_matched"] is True,
        "position_quantity_match": result["position_quantities_matched"] is True,
        "average_price_match": result["average_prices_matched"] is True,
        "market_value_match": result["market_values_matched"] is True,
        "unrealized_match": result["unrealized_pnl_matched"] is True,
        "open_order_match": result["open_order_count_matched"] is True,
        "reserved_match": result["reserved_buy_notional_matched"] is True,
        "mismatches_zero": result["mismatch_count"] == 0,
        "actual_positions_zero": result["actual_position_count"] == 0,
        "recovered_order_one": result["recovered_open_order_count"] == 1,
        "network_zero": result["read_requests_executed"] == 0,
        "write_zero": result["write_requests_executed"] == 0,
        "paper_orders_zero": result["actual_paper_orders_submitted"] == 0,
        "live_zero": result["live_orders_submitted"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V124.01-V125.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
