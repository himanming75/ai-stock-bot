from __future__ import annotations
import subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from web_controller.io import write_json
from web_controller.state import get_emergency

ALLOWED_ACTIONS={
    "run_v140":["tools/run_v140_final.py"],
    "run_offline_orchestrator":["tools/run_v137_01_to_v139_64.py"],
    "run_offline_shadow":["tools/run_v124_01_to_v126_64.py"],
}

def action_ledger(root:Path)->Path:
    return root/"release/v141_01_to_v145_64/actual/web_action_result.json"

def run_action(root:Path,name:str)->dict[str,Any]:
    emergency=get_emergency(root)
    if name not in ALLOWED_ACTIONS:
        return {"ok":False,"error":"ACTION_NOT_ALLOWED","action":name}
    if emergency.get("enabled") and name!="run_v140":
        return {
            "ok":False,
            "error":"EMERGENCY_STOP_ENABLED",
            "action":name,
            "emergency_stop":emergency,
        }
    cmd=[sys.executable,*ALLOWED_ACTIONS[name]]
    completed=subprocess.run(
        cmd,cwd=root,capture_output=True,text=True,timeout=120
    )
    result={
        "ok":completed.returncode==0,
        "action":name,
        "returncode":completed.returncode,
        "stdout":completed.stdout[-12000:],
        "stderr":completed.stderr[-12000:],
        "executed_at":datetime.now(timezone.utc).isoformat(),
        "actual_live_orders_submitted":0,
    }
    write_json(action_ledger(root),result)
    return result
