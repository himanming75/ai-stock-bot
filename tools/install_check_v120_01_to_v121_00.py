from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime import (
    AutonomousPaperReadSession,
    AutonomousPaperReadSnapshot,
)

assert AutonomousPaperReadSession
assert AutonomousPaperReadSnapshot

source = (
    ROOT / "release" / "v120_00" / "output"
    / "autonomous_alpaca_paper_runtime_foundation_result.json"
)
if not source.is_file():
    raise SystemExit(f"MISSING V120 FOUNDATION RESULT: {source}")

print("V120.01-V121.00 ACTUAL AUTONOMOUS PAPER READ SESSION INSTALL CHECK PASS")
