import importlib,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(root))
req=[
root/"paper_runtime/retry_approval_supervised_reentry_v83_41_44.py",
root/"dashboard/retry_approval_supervised_reentry_integration.py",
root/"tools/run_retry_approval_supervised_reentry_v83_41_to_v83_44.py",
root/"tools/test_retry_approval_supervised_reentry_v83_41_to_v83_44.py",
root/"tools/verify_retry_approval_supervised_reentry_v83_41_to_v83_44.py",
root/"release/v83_41_to_v83_44/input/retry_approval_policy.json"]
m=[str(x) for x in req if not x.exists()]
if m: raise SystemExit("MISSING:\n"+"\n".join(m))
importlib.import_module("paper_runtime.retry_approval_supervised_reentry_v83_41_44")
print("V83.41-V83.44 INSTALL CHECK PASS")
