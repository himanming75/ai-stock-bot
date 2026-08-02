from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.fill_reconciliation import (
    ActualOrderLifecycleFillReconciler,
    FillReconciliationState,
)

assert ActualOrderLifecycleFillReconciler
assert FillReconciliationState

required = (
    ROOT / "release/v128_00/actual"
    / "actual_existing_paper_order_lifecycle_result.json"
)
if not required.is_file():
    raise SystemExit(f"MISSING V128 ACTUAL LIFECYCLE RESULT: {required}")

print("V128.01-V129.00 ACTUAL ORDER LIFECYCLE FILL RECONCILIATION INSTALL CHECK PASS")
