import importlib
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
required = [
    root / "paper_runtime/full_schedule_completion_orchestrator_v83_57_60.py",
    root / "dashboard/full_schedule_completion_orchestrator_integration.py",
    root / "tools/run_full_schedule_completion_orchestrator_v83_57_to_v83_60.py",
    root / "tools/test_full_schedule_completion_orchestrator_v83_57_to_v83_60.py",
    root / "tools/verify_full_schedule_completion_orchestrator_v83_57_to_v83_60.py",
    root / "release/v83_57_to_v83_60/input/"
    "full_schedule_completion_orchestrator_policy.json",
]
missing = [str(path) for path in required if not path.exists()]
if missing:
    raise SystemExit("MISSING:\n" + "\n".join(missing))
importlib.import_module(
    "paper_runtime.full_schedule_completion_orchestrator_v83_57_60"
)
print("V83.57-V83.60 INSTALL CHECK PASS")
