from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from continuous_paper_runtime import (
    ContinuousPaperRuntime,
    ContinuousRuntimeConfig,
)

assert ContinuousPaperRuntime
assert ContinuousRuntimeConfig

source = (
    ROOT / "release" / "v117_00" / "output"
    / "paper_runtime_operational_stability_result.json"
)
if not source.is_file():
    raise SystemExit(f"MISSING V117 STABILITY RESULT: {source}")

print("V117.01-V118.00 CONTINUOUS PAPER RUNTIME RELEASE CANDIDATE INSTALL CHECK PASS")
