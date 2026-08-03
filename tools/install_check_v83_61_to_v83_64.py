import importlib
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
required = [
    root / "paper_runtime/crash_recovery_restart_continuation_v83_61_64.py",
    root / "dashboard/crash_recovery_restart_continuation_integration.py",
    root / "tools/run_crash_recovery_restart_continuation_v83_61_to_v83_64.py",
    root / "tools/test_crash_recovery_restart_continuation_v83_61_to_v83_64.py",
    root / "tools/verify_crash_recovery_restart_continuation_v83_61_to_v83_64.py",
    root / "release/v83_61_to_v83_64/input/"
    "crash_recovery_restart_policy.json",
]
missing = [str(path) for path in required if not path.exists()]
if missing:
    raise SystemExit("MISSING:\n" + "\n".join(missing))
importlib.import_module(
    "paper_runtime.crash_recovery_restart_continuation_v83_61_64"
)
print("V83.61-V83.64 INSTALL CHECK PASS")
