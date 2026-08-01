from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from execution_engine import PaperExecutionAdapter, PaperExecutionEngine, MockPaperTransport

assert PaperExecutionAdapter
assert PaperExecutionEngine
assert MockPaperTransport

source = ROOT / "release" / "v105_00" / "output" / "order_intent_position_sizing_result.json"
if not source.is_file():
    raise SystemExit(f"MISSING V105 ORDER INTENT RESULT: {source}")

print("V105.01-V106.00 PAPER EXECUTION ADAPTER INSTALL CHECK PASS")
