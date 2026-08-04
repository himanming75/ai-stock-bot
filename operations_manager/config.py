from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from operations_manager.io import load_json,write_json

DEFAULT={
    "timezone":"America/Los_Angeles",
    "web_controller_autostart_enabled":False,
    "pre_market_check_enabled":False,
    "intraday_shadow_enabled":False,
    "post_market_report_enabled":False,
    "automated_paper_submission_enabled":False,
    "pre_market_time":"06:20",
    "intraday_time":"07:00",
    "post_market_time":"13:10",
    "health_stale_minutes":30,
    "restart_on_failure":False,
    "desktop_notifications_enabled":True,
    "email_notifications_enabled":False,
    "telegram_notifications_enabled":False,
    "paper_only":True,
    "live_submission_enabled":False,
}

def path(root:Path)->Path:
    return root/"release/v156_01_to_v160_64/config/operations_manager.json"

def load(root:Path)->dict[str,Any]:
    value=load_json(path(root))
    if not value:
        value=deepcopy(DEFAULT)
        value["updated_at"]=datetime.now(timezone.utc).isoformat()
        write_json(path(root),value)
    return value

def _valid_time(value:Any)->bool:
    try:
        hour,minute=map(int,str(value).split(":"))
        return 0<=hour<=23 and 0<=minute<=59
    except Exception:
        return False

def validate(value:dict[str,Any])->dict[str,Any]:
    errors=[]
    for key in ("pre_market_time","intraday_time","post_market_time"):
        if not _valid_time(value.get(key)):
            errors.append(f"{key} must be HH:MM.")
    try: stale=int(value.get("health_stale_minutes",0))
    except Exception: stale=0
    if not 5<=stale<=1440:
        errors.append("health_stale_minutes must be 5-1440.")
    if value.get("paper_only") is not True:
        errors.append("Paper-only mode must remain enabled.")
    if value.get("live_submission_enabled") is not False:
        errors.append("Live submission must remain disabled.")
    if value.get("automated_paper_submission_enabled") is True:
        errors.append("Scheduled Paper order submission is not enabled in this release.")
    normalized=deepcopy(DEFAULT)
    for key in normalized:
        if key in value:
            normalized[key]=value[key]
    normalized["health_stale_minutes"]=stale or 30
    normalized["automated_paper_submission_enabled"]=False
    normalized["paper_only"]=True
    normalized["live_submission_enabled"]=False
    return {"valid":not errors,"errors":errors,"normalized":normalized}

def save(root:Path,value:dict[str,Any])->dict[str,Any]:
    result=validate(value)
    if not result["valid"]: return {"ok":False,**result}
    data=result["normalized"]
    data["updated_at"]=datetime.now(timezone.utc).isoformat()
    write_json(path(root),data)
    return {"ok":True,"config":data}
