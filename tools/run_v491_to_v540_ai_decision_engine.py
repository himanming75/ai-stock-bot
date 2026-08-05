from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_decision_engine.service import AIDecisionEngineService

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strategy",
        default=(
            "release/v461_490_strategy_framework/"
            "actual/strategy_framework_latest.json"
        ),
    )
    parser.add_argument(
        "--risk",
        default=(
            "release/v331_340_realtime_risk_monitoring/"
            "actual/risk_monitor_latest.json"
        ),
    )
    parser.add_argument(
        "--timeframes",
        default=(
            "release/v491_540_ai_decision_engine/"
            "fixtures/timeframe_signals_fixture.json"
        ),
    )
    parser.add_argument(
        "--policy",
        default=(
            "release/v491_540_ai_decision_engine/"
            "config/ai_decision_policy.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "release/v491_540_ai_decision_engine/actual"
        ),
    )
    args = parser.parse_args()

    result = AIDecisionEngineService().evaluate(
        strategy_path=Path(args.strategy),
        risk_path=Path(args.risk),
        timeframe_path=Path(args.timeframes),
        policy_path=Path(args.policy),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
