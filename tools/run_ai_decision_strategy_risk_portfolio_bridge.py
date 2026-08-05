from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from ai_decision_bridge.service import DecisionBridgeService

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--decision", default="release/ai_symbol_selection_decision_orchestration/actual/ai_decision_snapshot.json")
    p.add_argument("--config", default="release/ai_decision_strategy_risk_portfolio_bridge/config/bridge_config.json")
    p.add_argument("--output", default="release/ai_decision_strategy_risk_portfolio_bridge/actual/bridge_snapshot.json")
    a = p.parse_args()
    result = DecisionBridgeService().run_file(Path(a.decision), Path(a.config), Path(a.output))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2
if __name__ == "__main__": raise SystemExit(main())
