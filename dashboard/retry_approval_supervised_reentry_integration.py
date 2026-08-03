import json
from pathlib import Path
def build_retry_approval_supervised_reentry_payload(root: Path):
    path=root/"release/v83_41_to_v83_44/actual/retry_approval_supervised_reentry_dashboard_state.json"
    if not path.exists(): return {"retry_approval_state":"NOT_AVAILABLE"}
    try: value=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError): return {"retry_approval_state":"NOT_AVAILABLE"}
    return value if isinstance(value,dict) else {"retry_approval_state":"NOT_AVAILABLE"}
