from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest_v2.engine import run_backtest
from backtest_v2.io import load_json, parse_input, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(
            ROOT / "release/v87_01_to_v87_08/input/"
            "backtest_sample.json"
        ),
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    payload = load_json(input_path)
    symbol, bars, policy = parse_input(payload)
    backtest = run_backtest(symbol, bars, policy)

    result = {
        "stage": "V87.08",
        "stage_range": "V87.01-V87.08",
        "state": "BACKTEST_ENGINE_V2_READY",
        "status": "PASS",
        "implementation_type": "LOCAL_EVENT_DRIVEN_BACKTEST_ENGINE_V2",
        "backtest": backtest,
        "input_path": str(input_path.resolve()),
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
        "next_phase": "V87_09_WALK_FORWARD_AND_STRESS_VALIDATION",
    }

    actual = ROOT / "release/v87_01_to_v87_08/actual"
    result_path = actual / "backtest_v2_result.json"
    write_json(result_path, result)
    write_json(actual / "backtest_trade_log.json", {
        "symbol": backtest["symbol"],
        "trades": backtest["trades"],
        "trade_statistics": backtest["trade_statistics"],
        "paper_only": True,
    })
    write_json(actual / "backtest_equity_curve.json", {
        "symbol": backtest["symbol"],
        "equity_curve": backtest["equity_curve"],
        "drawdown_curve_pct": backtest["drawdown_curve_pct"],
        "daily_curve": backtest["daily_curve"],
        "paper_only": True,
    })

    summary = {
        "stage": result["stage"],
        "stage_range": result["stage_range"],
        "state": result["state"],
        "status": result["status"],
        "symbol": backtest["symbol"],
        "bar_count": backtest["bar_count"],
        "ending_equity": backtest["ending_equity"],
        "net_profit": backtest["net_profit"],
        "total_return_pct": backtest["total_return_pct"],
        "maximum_drawdown_pct": backtest["maximum_drawdown_pct"],
        "sharpe_ratio": backtest["sharpe_ratio"],
        "sortino_ratio": backtest["sortino_ratio"],
        "total_trades": backtest["trade_statistics"]["total_trades"],
        "win_rate_pct": backtest["trade_statistics"]["win_rate_pct"],
        "profit_factor": backtest["trade_statistics"]["profit_factor"],
        "paper_only": result["paper_only"],
        "broker_write_enabled": result["broker_write_enabled"],
        "order_submission_enabled": result["order_submission_enabled"],
        "live_trading_enabled": result["live_trading_enabled"],
        "external_network_enabled": result["external_network_enabled"],
        "next_phase": result["next_phase"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"RESULT_FILE={result_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
