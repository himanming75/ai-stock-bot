from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from unified_ai_decision_reasoning.service import (
    UnifiedAIDecisionReasoningService,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ensemble",
        default=(
            "release/v1201_1400_multi_strategy_ensemble/"
            "actual/multi_strategy_ensemble_latest.json"
        ),
    )
    parser.add_argument(
        "--news",
        default=(
            "release/v1401_1600_news_earnings_macro/"
            "actual/news_earnings_macro_latest.json"
        ),
    )
    parser.add_argument(
        "--fundamental",
        default=(
            "release/v1601_1800_fundamental_sector_options/"
            "actual/fundamental_sector_options_latest.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "release/v1801_2000_unified_ai_decision/actual"
        ),
    )
    args = parser.parse_args()

    result = UnifiedAIDecisionReasoningService().evaluate(
        ensemble_path=Path(args.ensemble),
        news_path=Path(args.news),
        fundamental_path=Path(args.fundamental),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PASS", "PARTIAL_INPUT"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
