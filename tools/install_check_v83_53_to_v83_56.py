import importlib
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
required = [
    root / "paper_runtime/retry_cycle_completion_v83_53_56.py",
    root / "dashboard/retry_cycle_completion_integration.py",
    root / "tools/run_retry_cycle_completion_v83_53_to_v83_56.py",
    root / "tools/test_retry_cycle_completion_v83_53_to_v83_56.py",
    root / "tools/verify_retry_cycle_completion_v83_53_to_v83_56.py",
    root / "release/v83_53_to_v83_56/input/"
    "retry_cycle_completion_policy.json",
]
missing = [str(path) for path in required if not path.exists()]
if missing:
    raise SystemExit("MISSING:\n" + "\n".join(missing))
importlib.import_module("paper_runtime.retry_cycle_completion_v83_53_56")
print("V83.53-V83.56 INSTALL CHECK PASS")
