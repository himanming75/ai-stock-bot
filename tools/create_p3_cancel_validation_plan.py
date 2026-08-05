from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from p3_cancel_validation.plan import create_cancel_plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="SPY")
    parser.add_argument("--notional", default="5")
    parser.add_argument("--price-multiplier", default="0.50")
    parser.add_argument(
        "--output",
        default=(
            "release/p3_cancel_validation/actual/"
            "cancel_validation_plan.json"
        ),
    )
    args = parser.parse_args()

    plan = create_cancel_plan(
        symbol=args.symbol,
        notional=Decimal(args.notional),
        price_multiplier=Decimal(args.price_multiplier),
        output_path=Path(args.output),
    )
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0 if not plan["blocked"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
