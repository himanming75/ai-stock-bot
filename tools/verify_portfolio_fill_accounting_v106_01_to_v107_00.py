from pathlib import Path
from decimal import Decimal
import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    result = json.loads(
        (
            Path(args.repository_root).resolve()
            / "release"
            / "v107_00"
            / "output"
            / "portfolio_fill_accounting_result.json"
        ).read_text(encoding="utf-8")
    )
    stats = result["stats"]
    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "PORTFOLIO_FILL_ACCOUNTING_FOUNDATION",
        "fills_three": stats["fills_processed"] == 3,
        "partial_two": stats["partial_fills_processed"] == 2,
        "full_one": stats["full_fills_processed"] == 1,
        "snapshots_three": result["snapshot_event_count"] == 3,
        "position_half": Decimal(result["position_quantity"]) == Decimal("0.5"),
        "average_price_51": Decimal(result["position_average_price"]) == Decimal("51"),
        "realized_positive": Decimal(result["realized_pnl"]) == Decimal("2.5"),
        "unrealized_before_sell_four": Decimal(result["unrealized_pnl_before_sell"]) == Decimal("4"),
        "network_zero": result["network_requests_executed"] == 0,
        "paper_orders_zero": result["actual_paper_orders_submitted"] == 0,
        "live_orders_zero": result["live_orders_submitted"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V106.01-V107.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
