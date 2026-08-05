from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from multi_strategy_ensemble.service import MultiStrategyEnsembleService

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--feature-vector",
        default="release/v1001_1200_ai_market_intelligence/actual/feature_vector_latest.json",
    )
    parser.add_argument(
        "--market-regime",
        default="release/v1001_1200_ai_market_intelligence/actual/market_regime_latest.json",
    )
    parser.add_argument(
        "--output-dir",
        default="release/v1201_1400_multi_strategy_ensemble/actual",
    )
    args = parser.parse_args()
    result = MultiStrategyEnsembleService().evaluate(
        Path(args.feature_vector), Path(args.market_regime), Path(args.output_dir)
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
