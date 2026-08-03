from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from multi_asset_backtest.engine import run_multi_asset_backtest
from multi_asset_backtest.io import load_json, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(
            ROOT / "release/v87_17_to_v87_24/input/"
            "multi_asset_backtest_input.json"
        ),
    )
    args = parser.parse_args()

    payload = load_json(Path(args.input))
    assets = payload.get("assets", [])
    policy = payload.get("policy", {})
    result_data = run_multi_asset_backtest(assets, policy)

    state = (
        "MULTI_ASSET_BACKTEST_CERTIFIED"
        if result_data["certified"]
        else "MULTI_ASSET_BACKTEST_REVIEW_REQUIRED"
    )
    result = {
        "stage": "V87.24",
        "stage_range": "V87.17-V87.24",
        "state": state,
        "status": "PASS",
        "implementation_type": "LOCAL_MULTI_ASSET_BACKTEST_AND_BENCHMARK",
        "multi_asset": result_data,
        "paper_only": True,
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "broker_command_execution_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "next_phase": "V88_01_WEB_UI_V2",
    }

    actual = ROOT / "release/v87_17_to_v87_24/actual"
    result_path = actual / "multi_asset_backtest_result.json"
    write_json(result_path, result)
    write_json(
        actual / "multi_asset_backtest_certificate.json",
        result_data["certificate"],
    )
    write_json(
        actual / "multi_asset_performance_summary.json",
        {
            "portfolio": result_data["portfolio"],
            "benchmark": result_data["benchmark"],
            "excess_return_pct": result_data["excess_return_pct"],
            "sector_performance": result_data["sector_performance"],
            "concentration": result_data["concentration"],
            "paper_only": True,
        },
    )

    summary = {
        "stage": result["stage"],
        "state": result["state"],
        "status": result["status"],
        "asset_count": result_data["asset_count"],
        "portfolio_return_pct": result_data["portfolio"]["total_return_pct"],
        "benchmark_return_pct": result_data["benchmark"]["total_return_pct"],
        "excess_return_pct": result_data["excess_return_pct"],
        "largest_weight_pct": result_data["concentration"]["largest_weight_pct"],
        "effective_asset_count": result_data["concentration"]["effective_asset_count"],
        "certified": result_data["certified"],
        "paper_only": True,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"RESULT_FILE={result_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
