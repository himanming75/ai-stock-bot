from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.completion_unlock_gate import (
    CompletionGateState,
    CompletionLedger,
    OrderCompletionNextOrderUnlockGate,
)

assert CompletionGateState
assert CompletionLedger
assert OrderCompletionNextOrderUnlockGate

required = (
    ROOT / "release/v130_00/actual"
    / "actual_existing_paper_order_lifecycle_monitor_result.json"
)
if not required.is_file():
    raise SystemExit(f"MISSING V130 ACTUAL MONITOR RESULT: {required}")

print("V130.01-V131.00 ORDER COMPLETION NEXT ORDER UNLOCK INSTALL CHECK PASS")
