from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from risk_engine_v2.io import load_json,write_json

def path(root:Path)->Path:
    return root/"release/v206_01_to_v210_64/control/risk_kill_switch.json"

def load(root:Path)->dict:
    value=load_json(path(root))
    if not value:
        value={"enabled":True,"reason":"DEFAULT_SAFE_START","updated_at":datetime.now(timezone.utc).isoformat()}
        write_json(path(root),value)
    return value

def set_state(root:Path,enabled:bool,reason:str)->dict:
    value={"enabled":enabled,"reason":reason or ("MANUAL_STOP" if enabled else "MANUAL_CLEAR"),"updated_at":datetime.now(timezone.utc).isoformat()}
    write_json(path(root),value)
    return value
