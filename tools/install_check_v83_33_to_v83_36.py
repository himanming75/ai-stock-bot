import importlib
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
required = [
    root / "paper_runtime/trigger_recovery_dispatch_chain_v83_33_36.py",
    root / "dashboard/trigger_recovery_dispatch_chain_integration.py",
    root / "tools/run_trigger_recovery_dispatch_chain_v83_33_to_v83_36.py",
    root / "tools/test_trigger_recovery_dispatch_chain_v83_33_to_v83_36.py",
    root / "tools/verify_trigger_recovery_dispatch_chain_v83_33_to_v83_36.py",
    root / "release/v83_33_to_v83_36/input/"
    "trigger_recovery_dispatch_chain_policy.json",
]
missing = [str(path) for path in required if not path.exists()]
if missing:
    raise SystemExit("MISSING:\n" + "\n".join(missing))
importlib.import_module(
    "paper_runtime.trigger_recovery_dispatch_chain_v83_33_36"
)
print("V83.33-V83.36 INSTALL CHECK PASS")
