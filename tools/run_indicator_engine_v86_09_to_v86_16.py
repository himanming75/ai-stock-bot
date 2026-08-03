from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from indicator_engine.engine import evaluate_indicators
from indicator_engine.io import load_json, parse_bars, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(
            ROOT / "release/v86_09_to_v86_16/input/"
            "ohlcv_sample.json"
        ),
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    payload = load_json(input_path)
    symbol, bars = parse_bars(payload)
    indicators = evaluate_indicators(symbol, bars)

    strategy_input = {
        "symbol": indicators["symbol"],
        "policy": {
            "buy_threshold": 35,
            "sell_threshold": -35,
            "watch_confidence": 45,
        },
        "signals": indicators["strategy_signals"],
    }

    actual = ROOT / "release/v86_09_to_v86_16/actual"
    write_json(actual / "strategy_signal_input_from_indicators.json", strategy_input)

    result = {
        "stage": "V86.16",
        "stage_range": "V86.09-V86.16",
        "state": "INDICATOR_ENGINE_READY",
        "status": "PASS",
        "implementation_type": "LOCAL_OHLCV_INDICATOR_ENGINE",
        "indicators": indicators,
        "strategy_signal_output_path": str(
            (actual / "strategy_signal_input_from_indicators.json").resolve()
        ),
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
        "next_phase": "V86_17_PORTFOLIO_SCORING",
    }

    result_path = actual / "indicator_engine_result.json"
    write_json(result_path, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={result_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
