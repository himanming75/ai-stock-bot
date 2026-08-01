from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_broker import (
    AlpacaPaperOrderRecoveryManager,
    AtomicPaperOrderRecoveryStore,
    PaperOrderRecoveryRecord,
)

assert AlpacaPaperOrderRecoveryManager
assert AtomicPaperOrderRecoveryStore
assert PaperOrderRecoveryRecord

source = (
    ROOT / "release" / "v113_00" / "output"
    / "actual_alpaca_paper_order_validation_fixture_result.json"
)
if not source.is_file():
    raise SystemExit(f"MISSING V113 VALIDATION RESULT: {source}")

print("V113.01-V114.00 ALPACA PAPER ORDER RECOVERY RESTART INSTALL CHECK PASS")
