from pathlib import Path
import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    result_path = Path(args.repository_root).resolve() / "release" / "v103_00" / "output" / "market_data_foundation_result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    stats = result["routing_stats"]
    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "REALTIME_MARKET_DATA_FOUNDATION",
        "three_messages_published": result["stream_result"]["published_count"] == 3,
        "duplicate_rejected": stats["duplicates"] == 1,
        "unsubscribed_rejected": stats["unsubscribed"] == 1,
        "events_three": result["event_count"] == 3,
        "connection_stopped": result["connection_state"] == "STOPPED",
        "backoff_capped": result["backoff_preview_seconds"] == [1, 2, 4, 8, 8],
        "network_disabled": result["network_connection_enabled"] is False,
        "network_zero": result["network_requests_executed"] == 0,
        "paper_submit_disabled": result["paper_order_submission_enabled"] is False,
        "orders_zero": result["actual_orders_submitted"] == 0,
        "live_disabled": result["live_trading_enabled"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V102.01-V103.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
