from __future__ import annotations
import json
from pathlib import Path

def build_automated_orchestrator_payload(root: Path):
    p=root/'release/v83_01_to_v83_04/actual/automated_orchestrator_dashboard_state.json'
    if not p.exists(): return {'orchestrator_state':'NOT_AVAILABLE'}
    try: v=json.loads(p.read_text(encoding='utf-8'))
    except Exception: return {'orchestrator_state':'NOT_AVAILABLE'}
    return v if isinstance(v,dict) else {'orchestrator_state':'NOT_AVAILABLE'}
