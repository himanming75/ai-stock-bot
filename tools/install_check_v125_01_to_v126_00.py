from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.safe_mode_gate import (
    AutonomousSafeModeRecoveryGate,
    RecoveryGateState,
)

assert AutonomousSafeModeRecoveryGate
assert RecoveryGateState

required = [
    ROOT / "release/v124_00/actual_read/actual_order_ledger_recovery_result.json",
    ROOT / "release/v125_00/actual_read/actual_broker_portfolio_reconciliation_result.json",
]
missing = [str(path) for path in required if not path.is_file()]
if missing:
    raise SystemExit("MISSING PREREQUISITES: " + ", ".join(missing))

print("V125.01-V126.00 AUTONOMOUS SAFE-MODE RECOVERY GATE INSTALL CHECK PASS")
