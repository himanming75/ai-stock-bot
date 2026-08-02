from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime import (
    AutonomousPaperOrderIdentityReconciler,
    OrderIdentityPolicy,
    OrderIdentityStatus,
)

assert AutonomousPaperOrderIdentityReconciler
assert OrderIdentityPolicy
assert OrderIdentityStatus

source = (
    ROOT / "release" / "v122_00" / "output"
    / "autonomous_paper_read_reconciliation_result.json"
)
if not source.is_file():
    raise SystemExit(f"MISSING V122 RECONCILIATION RESULT: {source}")

print("V122.01-V123.00 AUTONOMOUS PAPER ORDER IDENTITY RECONCILIATION INSTALL CHECK PASS")
