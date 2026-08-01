from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from execution_engine import OrderIntentEngine, PositionSizer

assert OrderIntentEngine
assert PositionSizer

source = ROOT / "release" / "v104_00" / "output" / "strategy_signal_engine_result.json"
if not source.is_file():
    raise SystemExit(f"MISSING V104 STRATEGY RESULT: {source}")

print("V104.01-V105.00 ORDER INTENT POSITION SIZING INSTALL CHECK PASS")
