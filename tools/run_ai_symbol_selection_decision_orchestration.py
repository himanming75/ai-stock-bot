from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_decision_orchestration.service import AIDecisionOrchestrationService


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--market",
        default="release/market_intelligence_data_fusion/actual/market_intelligence_snapshot.json",
    )
    parser.add_argument(
        "--policy",
        default="release/ai_symbol_selection_decision_orchestration/config/decision_policy.json",
    )
    parser.add_argument(
        "--output",
        default="release/ai_symbol_selection_decision_orchestration/actual/ai_decision_snapshot.json",
    )
    args = parser.parse_args()
    payload = AIDecisionOrchestrationService().run_file(
        Path(args.market), Path(args.policy), Path(args.output)
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
