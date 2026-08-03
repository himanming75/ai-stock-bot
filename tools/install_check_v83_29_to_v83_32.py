import importlib
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
required = [
    root / "paper_runtime/local_trigger_dispatcher_v83_29_32.py",
    root / "dashboard/local_trigger_dispatcher_integration.py",
    root / "tools/run_local_trigger_dispatcher_v83_29_to_v83_32.py",
    root / "tools/test_local_trigger_dispatcher_v83_29_to_v83_32.py",
    root / "release/v83_29_to_v83_32/input/local_trigger_dispatcher_policy.json",
]
missing = [str(path) for path in required if not path.exists()]
if missing:
    raise SystemExit("MISSING:\n" + "\n".join(missing))
importlib.import_module("paper_runtime.local_trigger_dispatcher_v83_29_32")
print("V83.29-V83.32 INSTALL CHECK PASS")
