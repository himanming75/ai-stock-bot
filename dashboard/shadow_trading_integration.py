from __future__ import annotations
import json
from pathlib import Path
from typing import Any

def build_shadow_trading_payload(root:Path)->dict[str,Any]:
    p=root/"release/v81_01_to_v81_04/actual/shadow_trading_dashboard_state.json"
    if not p.exists(): return {"shadow_state":"NOT_AVAILABLE"}
    try: v=json.loads(p.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError): return {"shadow_state":"NOT_AVAILABLE"}
    return v if isinstance(v,dict) else {"shadow_state":"NOT_AVAILABLE"}
