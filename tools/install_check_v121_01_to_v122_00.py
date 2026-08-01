from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime import (
    AutonomousPaperReadReconciler,
    ReconciliationPolicy,
    ReconciliationStatus,
)

assert AutonomousPaperReadReconciler
assert ReconciliationPolicy
assert ReconciliationStatus

source = (
    ROOT / "release" / "v121_00" / "actual_read"
    / "actual_autonomous_paper_read_result.json"
)
fixture = (
    ROOT / "release" / "v121_00" / "output"
    / "actual_autonomous_paper_read_fixture_result.json"
)
if not source.is_file() and not fixture.is_file():
    raise SystemExit("MISSING V121 ACTUAL OR FIXTURE READ RESULT")

print("V121.01-V122.00 AUTONOMOUS PAPER READ RECONCILIATION INSTALL CHECK PASS")
