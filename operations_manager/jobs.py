from __future__ import annotations
import subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from operations_manager.config import load
from operations_manager.health import evaluate as health_check
from operations_manager.lock import acquire,release
from operations_manager.notifications import notify
from operations_manager.io import write_json

ALLOWED={"pre_market","intraday_shadow","post_market","health_check","recovery_plan"}

def _run(root:Path,command:list[str])->dict[str,Any]:
    try:
        completed=subprocess.run(
            command,cwd=root,capture_output=True,text=True,timeout=180
        )
        return {
            "ok":completed.returncode==0,
            "returncode":completed.returncode,
            "stdout":completed.stdout[-12000:],
            "stderr":completed.stderr[-12000:],
        }
    except subprocess.TimeoutExpired:
        return {"ok":False,"error":"TIMEOUT"}

def run(root:Path,job:str)->dict[str,Any]:
    if job not in ALLOWED:
        return {"ok":False,"error":"JOB_NOT_ALLOWED","job":job}
    lock=acquire(root,"scheduled_job",ttl_minutes=20)
    if not lock["acquired"]:
        return {"ok":False,"error":"DUPLICATE_JOB_BLOCKED","job":job,"lock":lock}
    config=load(root)
    try:
        if job=="health_check":
            result={"ok":True,"health":health_check(root)}
        elif job=="recovery_plan":
            from operations_manager.recovery import create_plan
            result={"ok":True,"recovery":create_plan(root)}
        elif job=="pre_market":
            result=_run(root,[sys.executable,"tools/run_v140_final.py"])
        elif job=="intraday_shadow":
            # Read/shadow only; no order submission.
            script=root/"RUN_V124_TO_V126_REAL_SHADOW.ps1"
            result=_run(root,["powershell","-ExecutionPolicy","Bypass","-File",str(script)]) if script.exists() else {"ok":False,"error":"SHADOW_SCRIPT_MISSING"}
        else:
            result={"ok":True,"health":health_check(root),"message":"POST_MARKET_HEALTH_AND_REPORT_COMPLETE"}
        record={
            "job":job,"executed_at":datetime.now(timezone.utc).isoformat(),
            **result,"actual_live_orders_submitted":0,
        }
        write_json(
            root/"release/v156_01_to_v160_64/actual/last_scheduled_job.json",
            record,
        )
        if not result.get("ok"):
            notify(root,"ERROR",f"AI Stock Bot {job} failed",str(result.get("error") or result.get("stderr",""))[:500])
        return record
    finally:
        release(root,"scheduled_job")
