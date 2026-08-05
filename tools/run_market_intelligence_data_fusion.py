from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from market_intelligence.service import MarketIntelligenceFusionService


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="release/market_intelligence_data_fusion/fixtures/sample_market_data.json",
    )
    parser.add_argument(
        "--output",
        default="release/market_intelligence_data_fusion/actual/market_intelligence_snapshot.json",
    )
    args = parser.parse_args()

    result = MarketIntelligenceFusionService().run_file(Path(args.input), Path(args.output))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
