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
            / "v104_00"
            / "output"
            / "strategy_signal_engine_result.json"
        ).read_text(encoding="utf-8")
    )
    stats = result["stats"]
    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "STRATEGY_SIGNAL_ENGINE_FOUNDATION",
        "first_buy_accepted": result["first_signal_count"] == 1,
        "duplicate_rejected": result["duplicate_signal_count"] == 0,
        "sell_accepted": result["sell_signal_count"] == 1,
        "two_events_published": result["published_event_count"] == 2,
        "actions_buy_sell": result["published_actions"] == ["BUY", "SELL"],
        "evaluated_three": stats["evaluated"] == 3,
        "accepted_two": stats["accepted"] == 2,
        "duplicate_one": stats["rejected_duplicate"] == 1,
        "order_intents_zero": result["order_intents_created"] == 0,
        "paper_submit_disabled": result["paper_order_submission_enabled"] is False,
        "network_write_disabled": result["network_write_enabled"] is False,
        "orders_zero": result["actual_orders_submitted"] == 0,
        "live_disabled": result["live_trading_enabled"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V103.01-V104.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
