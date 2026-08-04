from __future__ import annotations
import os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from paper_web_ops.io import write_json
from paper_web_ops.settings import load as load_settings
from web_controller.state import get_emergency

def _result_path(root:Path)->Path:
    return root/"release/v151_01_to_v155_64/actual/last_paper_web_action.json"

def _finish(root:Path,result:dict[str,Any])->dict[str,Any]:
    result["executed_at"]=datetime.now(timezone.utc).isoformat()
    result["actual_live_orders_submitted"]=0
    write_json(_result_path(root),result)
    return result

def _credentials_ready()->bool:
    return bool(os.environ.get("ALPACA_PAPER_API_KEY")) and bool(os.environ.get("ALPACA_PAPER_SECRET_KEY"))

def _run(root:Path,cmd:list[str],env:dict[str,str]|None=None)->dict[str,Any]:
    try:
        completed=subprocess.run(
            cmd,cwd=root,capture_output=True,text=True,
            timeout=180,env=env,
        )
    except subprocess.TimeoutExpired:
        return {"ok":False,"error":"ACTION_TIMEOUT","command":cmd}
    return {
        "ok":completed.returncode==0,
        "returncode":completed.returncode,
        "stdout":completed.stdout[-16000:],
        "stderr":completed.stderr[-16000:],
        "command":cmd,
    }

def execute(root:Path,action:str,confirmation:str="")->dict[str,Any]:
    settings=load_settings(root)
    if action not in {"refresh_real_paper","run_real_shadow","submit_one_paper_cycle"}:
        return _finish(root,{"ok":False,"action":action,"error":"ACTION_NOT_ALLOWED"})
    if not _credentials_ready():
        return _finish(root,{"ok":False,"action":action,"error":"PAPER_CREDENTIALS_MISSING"})

    if action=="refresh_real_paper":
        if not settings.get("real_paper_read_enabled"):
            return _finish(root,{"ok":False,"action":action,"error":"REAL_PAPER_READ_DISABLED"})
        script=root/"RUN_V121_TO_V123_REAL_READ_ONLY.ps1"
        if not script.exists():
            return _finish(root,{"ok":False,"action":action,"error":"READ_ONLY_SCRIPT_NOT_FOUND"})
        result=_run(root,[
            "powershell","-ExecutionPolicy","Bypass","-File",str(script)
        ])
        return _finish(root,{"action":action,**result})

    if action=="run_real_shadow":
        if not settings.get("real_paper_shadow_enabled"):
            return _finish(root,{"ok":False,"action":action,"error":"REAL_PAPER_SHADOW_DISABLED"})
        script=root/"RUN_V124_TO_V126_REAL_SHADOW.ps1"
        if not script.exists():
            return _finish(root,{"ok":False,"action":action,"error":"REAL_SHADOW_SCRIPT_NOT_FOUND"})
        result=_run(root,[
            "powershell","-ExecutionPolicy","Bypass","-File",str(script)
        ])
        return _finish(root,{"action":action,**result})

    if get_emergency(root).get("enabled"):
        return _finish(root,{"ok":False,"action":action,"error":"EMERGENCY_STOP_ENABLED"})
    if settings.get("paper_submission_enabled") is not True:
        return _finish(root,{"ok":False,"action":action,"error":"PAPER_SUBMISSION_DISABLED"})
    if confirmation.strip().upper()!="PAPER ONLY":
        return _finish(root,{"ok":False,"action":action,"error":"CONFIRMATION_REQUIRED"})
    tool=root/"tools/run_v124_01_to_v126_64.py"
    if not tool.exists():
        return _finish(root,{"ok":False,"action":action,"error":"PAPER_CYCLE_TOOL_NOT_FOUND"})
    env=dict(os.environ)
    env["ALPACA_ALLOW_REAL_PAPER_NETWORK"]="YES"
    env["ALPACA_ALLOW_AUTOMATED_PAPER_ORDERS"]="YES"
    result=_run(root,[
        sys.executable,str(tool),"--real-network","--submit-paper"
    ],env=env)
    return _finish(root,{"action":action,**result})
