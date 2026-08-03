import json
from pathlib import Path
def build_reentry_execution_guard_audit_payload(root: Path):
    path=root/"release/v83_45_to_v83_48/actual/reentry_execution_guard_audit_dashboard_state.json"
    if not path.exists(): return {"reentry_execution_guard_state":"NOT_AVAILABLE"}
    try: value=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError): return {"reentry_execution_guard_state":"NOT_AVAILABLE"}
    return value if isinstance(value,dict) else {"reentry_execution_guard_state":"NOT_AVAILABLE"}
