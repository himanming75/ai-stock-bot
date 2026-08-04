from __future__ import annotations
import subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from production_scheduler.config import load
from production_scheduler.io import write_json,append_jsonl
from production_scheduler.lock import acquire,release

ALLOWED={
    "pre_market",
    "market_open_health",
    "qualification_refresh",
    "portfolio_refresh",
    "post_market_report",
    "nightly_backup",
}

def command_for(root:Path,job:str)->list[str]:
    mapping={
        "pre_market":[sys.executable,"tools/run_v140_final.py"],
        "market_open_health":[sys.executable,"tools/run_v156_operations_job.py","health_check"],
        "qualification_refresh":[sys.executable,"tools/run_v161_01_to_v165_64.py"],
        "portfolio_refresh":[sys.executable,"tools/run_v181_01_to_v185_64.py"],
        "post_market_report":[sys.executable,"tools/run_v186_01_to_v190_64.py","--skip-backup"],
        "nightly_backup":[sys.executable,"tools/run_v186_01_to_v190_64.py"],
    }
    return mapping[job]

def _execute(root:Path,command:list[str])->dict[str,Any]:
    completed=subprocess.run(
        command,cwd=root,capture_output=True,text=True,timeout=300,
    )
    return {
        "ok":completed.returncode==0,
        "returncode":completed.returncode,
        "stdout":completed.stdout[-16000:],
        "stderr":completed.stderr[-16000:],
    }

def run(root:Path,job:str)->dict[str,Any]:
    if job not in ALLOWED:
        return {"ok":False,"error":"JOB_NOT_ALLOWED","job":job}
    config=load(root)
    lock=acquire(root,job,int(config["lock_ttl_minutes"]))
    if not lock["acquired"]:
        return {"ok":False,"error":"DUPLICATE_JOB_BLOCKED","job":job,"lock":lock}
    started=datetime.now(timezone.utc)
    attempts=[]
    try:
        command=command_for(root,job)
        for attempt in range(int(config["maximum_retries"])+1):
            try:
                result=_execute(root,command)
            except subprocess.TimeoutExpired:
                result={"ok":False,"error":"JOB_TIMEOUT","returncode":-1,"stdout":"","stderr":""}
            attempts.append({"attempt":attempt+1,**result})
            if result.get("ok"): break
            if attempt<int(config["maximum_retries"]):
                time.sleep(int(config["retry_delay_seconds"]))
        ok=bool(attempts and attempts[-1].get("ok"))
        finished=datetime.now(timezone.utc)
        record={
            "ok":ok,
            "job":job,
            "started_at":started.isoformat(),
            "finished_at":finished.isoformat(),
            "duration_seconds":round((finished-started).total_seconds(),3),
            "attempt_count":len(attempts),
            "attempts":attempts,
            "scheduled_order_submission_included":False,
            "broker_write_enabled":False,
            "actual_live_orders_submitted":0,
        }
        actual=root/"release/v191_01_to_v195_64/actual"
        write_json(actual/"last_scheduler_job.json",record)
        append_jsonl(actual/"production_scheduler_ledger.jsonl",{
            "job":job,"started_at":record["started_at"],"finished_at":record["finished_at"],
            "ok":ok,"attempt_count":len(attempts),
            "actual_live_orders_submitted":0,
        })
        return record
    finally:
        release(root,job)
