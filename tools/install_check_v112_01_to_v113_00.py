from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_broker import ActualPaperOrderValidator, OrderValidationPolicy

assert ActualPaperOrderValidator
assert OrderValidationPolicy

source = ROOT / "release" / "v112_00" / "output" / "controlled_alpaca_paper_order_fixture_result.json"
if not source.is_file():
    raise SystemExit(f"MISSING V112 ORDER OPT-IN RESULT: {source}")

print("V112.01-V113.00 ACTUAL ALPACA PAPER ORDER VALIDATION INSTALL CHECK PASS")
