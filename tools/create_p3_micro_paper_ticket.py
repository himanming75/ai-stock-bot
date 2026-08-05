from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from p3_micro_paper.ticket import create_micro_ticket


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="SPY")
    parser.add_argument("--notional", default="5")
    parser.add_argument(
        "--output",
        default="release/p3_micro_paper/actual/p3_micro_ticket.json",
    )
    args = parser.parse_args()

    ticket = create_micro_ticket(
        symbol=args.symbol,
        notional=Decimal(args.notional),
        output_path=Path(args.output),
    )
    print(json.dumps(ticket, indent=2, sort_keys=True))
    return 0 if not ticket["blocked"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
