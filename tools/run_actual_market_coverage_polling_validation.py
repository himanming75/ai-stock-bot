from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from actual_market_polling.service import ActualMarketPollingValidationService

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default="SPY,QQQ,IWM")
    parser.add_argument("--interval-seconds", type=int, default=60)
    parser.add_argument("--max-cycles", type=int, default=10)
    args = parser.parse_args()

    symbols = [x.strip().upper() for x in args.symbols.split(",") if x.strip()]
    result = ActualMarketPollingValidationService(ROOT).run(
        symbols=symbols,
        interval_seconds=max(1, args.interval_seconds),
        max_cycles=max(1, args.max_cycles),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
