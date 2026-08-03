import importlib,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(root))
req=[root/"paper_runtime/reentry_execution_guard_audit_v83_45_48.py",root/"dashboard/reentry_execution_guard_audit_integration.py",root/"tools/run_reentry_execution_guard_audit_v83_45_to_v83_48.py",root/"tools/test_reentry_execution_guard_audit_v83_45_to_v83_48.py",root/"tools/verify_reentry_execution_guard_audit_v83_45_to_v83_48.py",root/"release/v83_45_to_v83_48/input/reentry_execution_guard_policy.json"]
m=[str(x) for x in req if not x.exists()]
if m: raise SystemExit("MISSING:\n"+"\n".join(m))
importlib.import_module("paper_runtime.reentry_execution_guard_audit_v83_45_48")
print("V83.45-V83.48 INSTALL CHECK PASS")
