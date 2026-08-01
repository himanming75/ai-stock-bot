from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy_engine import SignalEngine, MovingAverageCrossStrategy

assert SignalEngine
assert MovingAverageCrossStrategy

source = ROOT / "release" / "v103_00" / "output" / "market_data_foundation_result.json"
if not source.is_file():
    raise SystemExit(f"MISSING V103 MARKET DATA RESULT: {source}")

print("V103.01-V104.00 STRATEGY SIGNAL ENGINE INSTALL CHECK PASS")
