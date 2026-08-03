from __future__ import annotations
import json
from pathlib import Path
from typing import Any
def build_shadow_execution_payload(root:Path)->dict[str,Any]:
 p=root/"release/v81_05_to_v81_08/actual/shadow_execution_dashboard_state.json"
 if not p.exists(): return {"execution_state":"NOT_AVAILABLE"}
 try: x=json.loads(p.read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError): return {"execution_state":"NOT_AVAILABLE"}
 return x if isinstance(x,dict) else {"execution_state":"NOT_AVAILABLE"}
