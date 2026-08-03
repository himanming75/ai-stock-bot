from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from explainability_engine.engine import build_explainability_report
from explainability_engine.io import load_json, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strategy-result",
        default=str(
            ROOT / "release/v86_01_to_v86_08/actual/"
            "strategy_engine_v2_result.json"
        ),
    )
    parser.add_argument(
        "--indicator-result",
        default=str(
            ROOT / "release/v86_09_to_v86_16/actual/"
            "indicator_engine_result.json"
        ),
    )
    parser.add_argument(
        "--portfolio-result",
        default=str(
            ROOT / "release/v86_17_to_v86_24/actual/"
            "portfolio_scoring_result.json"
        ),
    )
    args = parser.parse_args()

    strategy = load_json(Path(args.strategy_result))
    indicators = load_json(Path(args.indicator_result))
    portfolio = load_json(Path(args.portfolio_result))

    missing = [
        name for name, value in (
            ("strategy_result", strategy),
            ("indicator_result", indicators),
            ("portfolio_result", portfolio),
        )
        if not value
    ]
    if missing:
        print(json.dumps({
            "status": "BLOCKED",
            "missing_inputs": missing,
        }, indent=2))
        return 1

    report = build_explainability_report(
        strategy,
        indicators,
        portfolio,
    )
    result = {
        "stage": "V86.32",
        "stage_range": "V86.25-V86.32",
        "state": "AI_EXPLAINABILITY_ENGINE_READY",
        "status": "PASS",
        "implementation_type": "LOCAL_DETERMINISTIC_EXPLAINABILITY_ENGINE",
        "report": report,
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
        "next_phase": "V87_BACKTEST_ENGINE_V2",
    }

    actual = ROOT / "release/v86_25_to_v86_32/actual"
    result_path = actual / "ai_explainability_result.json"
    write_json(result_path, result)
    write_json(actual / "ai_explainability_report.json", report)

    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={result_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
