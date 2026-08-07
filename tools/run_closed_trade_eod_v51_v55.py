from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from closed_trade_eod_v51_v55 import ClosedTradeEODPipeline

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", default=".")
    p.add_argument("--allow-during-market", action="store_true")
    a = p.parse_args()

    result = ClosedTradeEODPipeline(
        Path(a.repository_root)
    ).run(allow_during_market=a.allow_during_market)

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") in {
        "PASS",
        "WAITING_FOR_MARKET_CLOSE",
    } else 2

if __name__ == "__main__":
    raise SystemExit(main())
