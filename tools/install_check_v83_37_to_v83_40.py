import importlib
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
required = [
    root / "paper_runtime/trigger_chain_retry_policy_v83_37_40.py",
    root / "dashboard/trigger_chain_retry_policy_integration.py",
    root / "tools/run_trigger_chain_retry_policy_v83_37_to_v83_40.py",
    root / "tools/test_trigger_chain_retry_policy_v83_37_to_v83_40.py",
    root / "tools/verify_trigger_chain_retry_policy_v83_37_to_v83_40.py",
    root / "release/v83_37_to_v83_40/input/"
    "trigger_chain_retry_policy.json",
]
missing = [str(path) for path in required if not path.exists()]
if missing:
    raise SystemExit("MISSING:\n" + "\n".join(missing))
importlib.import_module("paper_runtime.trigger_chain_retry_policy_v83_37_40")
print("V83.37-V83.40 INSTALL CHECK PASS")
