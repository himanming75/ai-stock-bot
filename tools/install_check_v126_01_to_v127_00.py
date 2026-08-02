from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.controlled_single_order import (
    ControlledAutonomousPaperSingleOrder,
    ControlledOrderDecision,
    ControlledSingleOrderPolicy,
)

assert ControlledAutonomousPaperSingleOrder
assert ControlledOrderDecision
assert ControlledSingleOrderPolicy

required = ROOT / "release/v126_00/readiness/paper_write_readiness_result.json"
if not required.is_file():
    raise SystemExit(f"MISSING READINESS CERTIFICATE: {required}")

print("V126.01-V127.00 CONTROLLED AUTONOMOUS PAPER SINGLE ORDER INSTALL CHECK PASS")
