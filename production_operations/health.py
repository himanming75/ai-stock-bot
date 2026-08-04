from __future__ import annotations
import os,shutil
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from production_operations.io import load_json,write_json
from production_operations.config import load

TRACKED=[
 "release/v140_final/actual/v140_final_release_result.json",
 "release/v161_01_to_v165_64/actual/paper_qualification_result.json",
 "release/v181_01_to_v185_64/actual/portfolio_broker_result.json",
]

def evaluate(root:Path)->dict[str,Any]:
    policy=load(root)
    disk=shutil.disk_usage(root)
    free_mb=round(disk.free/1024/1024,2)
    files={}
    for rel in TRACKED:
        p=root/rel
        files[rel]={"present":p.exists(),"size_bytes":p.stat().st_size if p.exists() else 0}
    log_bytes=sum(p.stat().st_size for p in root.rglob("*.jsonl") if p.is_file())
    checks={
        "minimum_free_disk":free_mb>=float(policy["health_minimum_free_disk_mb"]),
        "maximum_log_size":log_bytes/1024/1024<=float(policy["health_maximum_log_size_mb"]),
        "v140_present":files[TRACKED[0]]["present"],
        "qualification_present":files[TRACKED[1]]["present"],
        "portfolio_present":files[TRACKED[2]]["present"],
        "broker_write_disabled":policy.get("broker_write_enabled") is False,
        "live_submission_disabled":policy.get("live_submission_enabled") is False,
    }
    failed=[k for k,v in checks.items() if not v]
    result={
        "observed_at":datetime.now(timezone.utc).isoformat(),
        "status":"HEALTHY" if not failed else "ATTENTION_REQUIRED",
        "free_disk_mb":free_mb,
        "total_log_size_mb":round(log_bytes/1024/1024,4),
        "tracked_files":files,
        "checks":checks,
        "failed":failed,
        "actual_live_orders_submitted":0,
    }
    write_json(root/"release/v186_01_to_v190_64/actual/production_health.json",result)
    return result
