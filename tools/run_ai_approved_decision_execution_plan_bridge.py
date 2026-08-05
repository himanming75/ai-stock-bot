from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_execution_plan_bridge.service import ExecutionPlanBridgeService

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bridge",
        default="release/ai_decision_strategy_risk_portfolio_bridge/actual/bridge_snapshot.json",
    )
    parser.add_argument(
        "--config",
        default="release/ai_execution_plan_bridge/config/execution_bridge_config.json",
    )
    parser.add_argument(
        "--output",
        default="release/ai_execution_plan_bridge/actual/execution_plan_snapshot.json",
    )
    args = parser.parse_args()
    result = ExecutionPlanBridgeService().run_file(
        Path(args.bridge), Path(args.config), Path(args.output)
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
