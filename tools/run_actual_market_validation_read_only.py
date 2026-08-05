from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from actual_market_validation.service import run_validation
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default="SPY,QQQ,IWM")
    args = parser.parse_args()
    symbols = [x.strip().upper() for x in args.symbols.split(",") if x.strip()]
    result = run_validation(ROOT, symbols)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2
if __name__ == "__main__":
    raise SystemExit(main())
