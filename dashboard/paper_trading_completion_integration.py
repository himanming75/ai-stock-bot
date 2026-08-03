from __future__ import annotations
import json
from pathlib import Path
from typing import Any

def build_paper_trading_completion_payload(root:Path)->dict[str,Any]:
 p=root/'release/v80_01_to_v80_04/actual/paper_trading_completion_dashboard_state.json'
 if not p.exists():return {'completion_state':'NOT_AVAILABLE'}
 try:v=json.loads(p.read_text(encoding='utf-8'))
 except (OSError,json.JSONDecodeError):return {'completion_state':'NOT_AVAILABLE'}
 return v if isinstance(v,dict) else {'completion_state':'NOT_AVAILABLE'}
