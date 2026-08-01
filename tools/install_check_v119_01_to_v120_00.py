from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime import (
    AutonomousAlpacaPaperRuntime,
    AutonomousRuntimeConfig,
)

assert AutonomousAlpacaPaperRuntime
assert AutonomousRuntimeConfig

source = (
    ROOT / "release" / "v119_00" / "output"
    / "continuous_paper_runtime_final_certification_result.json"
)
if not source.is_file():
    raise SystemExit(f"MISSING V119 FINAL CERTIFICATION RESULT: {source}")

print("V119.01-V120.00 AUTONOMOUS ALPACA PAPER RUNTIME FOUNDATION INSTALL CHECK PASS")
