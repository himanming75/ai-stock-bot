from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from news_earnings_macro_intelligence.service import (
    NewsEarningsMacroIntelligenceService,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--news",
        default=(
            "release/v1401_1600_news_earnings_macro/"
            "fixtures/news_fixture.json"
        ),
    )
    parser.add_argument(
        "--earnings",
        default=(
            "release/v1401_1600_news_earnings_macro/"
            "fixtures/earnings_fixture.json"
        ),
    )
    parser.add_argument(
        "--macro",
        default=(
            "release/v1401_1600_news_earnings_macro/"
            "fixtures/macro_fixture.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "release/v1401_1600_news_earnings_macro/actual"
        ),
    )
    args = parser.parse_args()

    result = NewsEarningsMacroIntelligenceService().evaluate(
        news_path=Path(args.news),
        earnings_path=Path(args.earnings),
        macro_path=Path(args.macro),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
