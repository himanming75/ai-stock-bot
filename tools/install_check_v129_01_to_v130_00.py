from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.lifecycle_monitor import (
    ExistingPaperOrderLifecycleMonitor,
    LifecycleLedger,
    MonitorDecision,
)

assert ExistingPaperOrderLifecycleMonitor
assert LifecycleLedger
assert MonitorDecision

required = (
    ROOT / "release/v129_00/actual"
    / "actual_order_lifecycle_fill_reconciliation_result.json"
)
if not required.is_file():
    raise SystemExit(f"MISSING V129 ACTUAL RESULT: {required}")

print("V129.01-V130.00 EXISTING PAPER ORDER LIFECYCLE MONITOR INSTALL CHECK PASS")
