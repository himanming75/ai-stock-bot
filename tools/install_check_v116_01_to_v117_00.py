from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_runtime_stability import (
    OperationalStabilityConfig,
    OperationalStabilityController,
)

assert OperationalStabilityConfig
assert OperationalStabilityController

source = (
    ROOT / "release" / "v116_00" / "output"
    / "paper_runtime_scheduler_integration_result.json"
)
if not source.is_file():
    raise SystemExit(f"MISSING V116 INTEGRATION RESULT: {source}")

print("V116.01-V117.00 PAPER RUNTIME OPERATIONAL STABILITY INSTALL CHECK PASS")
