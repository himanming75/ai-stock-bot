from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from closed_trade_outcome_v41_v45 import ClosedTradeOutcomeCollector

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", default=".")
    a = p.parse_args()
    result = ClosedTradeOutcomeCollector(Path(a.repository_root)).run()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") in {"PASS", "BLOCKED"} else 2

if __name__ == "__main__":
    raise SystemExit(main())
