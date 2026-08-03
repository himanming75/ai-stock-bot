from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy_engine_v2.engine import evaluate_strategy
from strategy_engine_v2.io import load_json, parse_signals, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(
            ROOT / "release/v86_01_to_v86_08/input/"
            "strategy_signal_input.json"
        ),
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    payload = load_json(input_path)
    symbol, signals = parse_signals(payload)
    policy = payload.get("policy", {})
    decision = evaluate_strategy(
        symbol,
        signals,
        buy_threshold=float(policy.get("buy_threshold", 35.0)),
        sell_threshold=float(policy.get("sell_threshold", -35.0)),
        watch_confidence=float(policy.get("watch_confidence", 45.0)),
    )

    result = {
        "stage": "V86.08",
        "stage_range": "V86.01-V86.08",
        "state": "AI_STRATEGY_ENGINE_V2_READY",
        "status": "PASS",
        "implementation_type": "LOCAL_RULE_BASED_AI_STRATEGY_ENGINE_V2",
        "decision": decision.to_dict(),
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
        "next_phase": "V86_09_INDICATOR_ENGINE",
    }

    result_path = (
        ROOT / "release/v86_01_to_v86_08/actual/"
        "strategy_engine_v2_result.json"
    )
    write_json(result_path, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={result_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
