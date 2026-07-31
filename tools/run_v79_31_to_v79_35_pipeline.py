from pathlib import Path
import argparse
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_market_data import (
    GapFillConfig,
    build_gap_fill_certificate,
    load_fixture_bars,
    load_gap_tasks,
    load_jsonl_bars,
    run_gap_fill,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()

    root = Path(args.repository_root).resolve()
    output = root / "release/v79_35/output"
    execution_dir = output / "gap_fill"
    if args.clean and output.exists():
        shutil.rmtree(output)

    prior_sync = root / "release/v79_30/output/sync"
    existing_path = prior_sync / "alpaca_historical_bars.jsonl"
    queue_path = prior_sync / "alpaca_historical_bars.gap_fill_queue.json"
    fixture_path = root / "release/v79_32/fixtures/gap_fill_bars_v79_32.json"

    config = GapFillConfig()
    existing = load_jsonl_bars(existing_path)
    tasks = load_gap_tasks(queue_path, config)
    fixtures = load_fixture_bars(fixture_path)
    result = run_gap_fill(existing, tasks, fixtures, config, execution_dir)
    certificate = build_gap_fill_certificate(root, output, config, result)

    print(json.dumps({
        "stage_range": "V79.31-V79.35",
        "status": certificate["status"],
        "passed_stage_count": certificate["passed_stage_count"],
        "failed_stage_count": certificate["failed_stage_count"],
        **result["stats"],
        **result["completion"],
        "network_requests_executed": certificate["network_requests_executed"],
        "credentials_used": certificate["credentials_used"],
        "trading_client_created": certificate["trading_client_created"],
        "actual_orders_submitted": certificate["actual_orders_submitted"],
        "next_phase": certificate["next_phase"],
    }, indent=2, sort_keys=True))
    return 0 if certificate["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
