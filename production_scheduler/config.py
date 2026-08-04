from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from production_scheduler.io import load_json,write_json

DEFAULT={
    "timezone":"America/Los_Angeles",
    "enabled":False,
    "pre_market_enabled":False,
    "market_open_health_enabled":False,
    "qualification_refresh_enabled":False,
    "portfolio_refresh_enabled":False,
    "post_market_report_enabled":False,
    "nightly_backup_enabled":False,
    "pre_market_time":"06:20",
    "market_open_health_time":"06:35",
    "qualification_refresh_time":"12:00",
    "portfolio_refresh_time":"12:05",
    "post_market_report_time":"13:10",
    "nightly_backup_time":"23:30",
    "maximum_retries":2,
    "retry_delay_seconds":15,
    "lock_ttl_minutes":30,
    "scheduled_paper_submission_enabled":False,
    "scheduled_live_submission_enabled":False,
    "broker_write_enabled":False,
}

def path(root:Path)->Path:
    return root/"release/v191_01_to_v195_64/config/production_scheduler_policy.json"

def load(root:Path)->dict[str,Any]:
    value=load_json(path(root))
    if not value:
        value=deepcopy(DEFAULT)
        value["updated_at"]=datetime.now(timezone.utc).isoformat()
        write_json(path(root),value)
    return value

def _valid_time(value:Any)->bool:
    try:
        h,m=map(int,str(value).split(":"))
        return 0<=h<=23 and 0<=m<=59
    except Exception:
        return False

def validate(value:dict[str,Any])->dict[str,Any]:
    errors=[]
    for key in (
        "pre_market_time","market_open_health_time","qualification_refresh_time",
        "portfolio_refresh_time","post_market_report_time","nightly_backup_time",
    ):
        if not _valid_time(value.get(key)):
            errors.append(f"{key} must be HH:MM.")
    try: retries=int(value.get("maximum_retries",0))
    except Exception: retries=-1
    if not 0<=retries<=5: errors.append("maximum_retries must be 0-5.")
    try: delay=int(value.get("retry_delay_seconds",0))
    except Exception: delay=0
    if not 1<=delay<=300: errors.append("retry_delay_seconds must be 1-300.")
    try: ttl=int(value.get("lock_ttl_minutes",0))
    except Exception: ttl=0
    if not 5<=ttl<=180: errors.append("lock_ttl_minutes must be 5-180.")
    for key in (
        "scheduled_paper_submission_enabled",
        "scheduled_live_submission_enabled",
        "broker_write_enabled",
    ):
        if value.get(key) is not False:
            errors.append(f"{key} must remain disabled.")
    normalized=deepcopy(DEFAULT)
    normalized.update(value)
    normalized["maximum_retries"]=max(0,retries)
    normalized["retry_delay_seconds"]=max(1,delay)
    normalized["lock_ttl_minutes"]=max(5,ttl)
    normalized["scheduled_paper_submission_enabled"]=False
    normalized["scheduled_live_submission_enabled"]=False
    normalized["broker_write_enabled"]=False
    return {"valid":not errors,"errors":errors,"normalized":normalized}
