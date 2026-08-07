from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from closed_trade_analytics_v46_v50 import ClosedTradeAnalyticsReadiness

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", default=".")
    a = p.parse_args()
    result = ClosedTradeAnalyticsReadiness(
        Path(a.repository_root)
    ).run()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
