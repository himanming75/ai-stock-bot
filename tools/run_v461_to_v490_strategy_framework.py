from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy_framework.service import StrategyFrameworkService


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default=(
            "release/v461_490_strategy_framework/"
            "config/strategy_registry.json"
        ),
    )
    parser.add_argument(
        "--market-fixture",
        default=(
            "release/v461_490_strategy_framework/"
            "fixtures/market_bars_fixture.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "release/v461_490_strategy_framework/actual"
        ),
    )
    args = parser.parse_args()

    result = StrategyFrameworkService().evaluate(
        strategy_config_path=Path(args.config),
        market_fixture_path=Path(args.market_fixture),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
