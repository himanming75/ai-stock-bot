from pathlib import Path
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
            / "v105_00"
            / "output"
            / "order_intent_position_sizing_result.json"
        ).read_text(encoding="utf-8")
    )
    stats = result["stats"]
    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "ORDER_INTENT_POSITION_SIZING_FOUNDATION",
        "two_intents": result["intent_count"] == 2,
        "buy_sell": result["intent_sides"] == ["BUY", "SELL"],
        "signals_three": stats["signals_received"] == 3,
        "intents_three_created_before_filters": stats["intents_created"] == 3,
        "duplicate_one": stats["rejected_duplicate"] == 1,
        "published_two": stats["published"] == 2,
        "broker_zero": result["broker_requests_executed"] == 0,
        "paper_submit_disabled": result["paper_order_submission_enabled"] is False,
        "orders_zero": result["actual_orders_submitted"] == 0,
        "live_disabled": result["live_trading_enabled"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V104.01-V105.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
