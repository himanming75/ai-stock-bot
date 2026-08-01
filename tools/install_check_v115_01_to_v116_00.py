from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_runtime_scheduler import (
    PaperRuntimeSchedulerIntegration,
    RuntimeSchedulerIntegrationConfig,
)

assert PaperRuntimeSchedulerIntegration
assert RuntimeSchedulerIntegrationConfig

source = (
    ROOT / "release" / "v115_00" / "output"
    / "alpaca_paper_session_scheduler_result.json"
)
if not source.is_file():
    raise SystemExit(f"MISSING V115 SCHEDULER RESULT: {source}")

print("V115.01-V116.00 PAPER RUNTIME SCHEDULER INTEGRATION INSTALL CHECK PASS")
