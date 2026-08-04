from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from production_operations.io import load_json,write_json

DEFAULT={
 "report_timezone":"America/Los_Angeles",
 "daily_report_enabled":True,
 "weekly_report_enabled":True,
 "monthly_report_enabled":True,
 "backup_enabled":True,
 "maximum_backup_count":30,
 "backup_include_paths":[
   "release/v140_final/actual",
   "release/v161_01_to_v165_64/actual",
   "release/v181_01_to_v185_64/actual",
   "release/v146_01_to_v150_64/config",
   "release/v151_01_to_v155_64/config",
   "release/v156_01_to_v160_64/config"
 ],
 "health_minimum_free_disk_mb":1024,
 "health_maximum_log_size_mb":100,
 "broker_write_enabled":False,
 "live_submission_enabled":False
}

def path(root:Path)->Path:
    return root/"release/v186_01_to_v190_64/config/production_operations_policy.json"

def load(root:Path)->dict[str,Any]:
    value=load_json(path(root))
    if not value:
        value=deepcopy(DEFAULT)
        value["updated_at"]=datetime.now(timezone.utc).isoformat()
        write_json(path(root),value)
    return value

def validate(value:dict[str,Any])->dict[str,Any]:
    errors=[]
    try: count=int(value.get("maximum_backup_count",0))
    except Exception: count=0
    if not 1<=count<=365: errors.append("maximum_backup_count must be 1-365.")
    if not isinstance(value.get("backup_include_paths"),list):
        errors.append("backup_include_paths must be a list.")
    for key in ("broker_write_enabled","live_submission_enabled"):
        if value.get(key) is not False:
            errors.append(f"{key} must remain disabled.")
    normalized=deepcopy(DEFAULT)
    normalized.update(value)
    normalized["maximum_backup_count"]=count or 30
    normalized["broker_write_enabled"]=False
    normalized["live_submission_enabled"]=False
    return {"valid":not errors,"errors":errors,"normalized":normalized}
