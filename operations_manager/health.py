from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from operations_manager.config import load
from operations_manager.io import load_json,write_json

TRACKED={
    "v140":"release/v140_final/actual/v140_final_release_result.json",
    "paper":"release/v121_01_to_v123_64/actual/alpaca_paper_operations_result.json",
    "shadow":"release/v124_01_to_v126_64/actual/continuous_paper_shadow_result.json",
    "risk":"release/v134_01_to_v136_64/actual/dynamic_live_risk_result.json",
    "orchestrator":"release/v137_01_to_v139_64/actual/autonomous_orchestrator_result.json",
}

def evaluate(root:Path)->dict[str,Any]:
    config=load(root)
    now=datetime.now(timezone.utc)
    files={}
    for name,rel in TRACKED.items():
        path=root/rel
        age_minutes=None
        if path.exists():
            modified=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc)
            age_minutes=round((now-modified).total_seconds()/60,2)
        files[name]={
            "present":path.exists(),
            "age_minutes":age_minutes,
            "stale":age_minutes is not None and age_minutes>int(config["health_stale_minutes"]),
        }
    critical_present=files["v140"]["present"]
    historical_live_orders=0
    for rel in TRACKED.values():
        historical_live_orders+=int(load_json(root/rel).get("actual_live_orders_submitted",0))
    checks={
        "v140_present":critical_present,
        "historical_live_orders_zero":historical_live_orders==0,
        "paper_only":config.get("paper_only") is True,
        "live_submission_disabled":config.get("live_submission_enabled") is False,
        "scheduled_order_submission_disabled":config.get("automated_paper_submission_enabled") is False,
    }
    failed=[k for k,v in checks.items() if not v]
    result={
        "observed_at":now.isoformat(),
        "status":"HEALTHY" if not failed else "ATTENTION_REQUIRED",
        "checks":checks,"failed":failed,"tracked_files":files,
        "historical_live_orders_submitted":historical_live_orders,
        "actual_live_orders_submitted":0,
    }
    write_json(
        root/"release/v156_01_to_v160_64/actual/health_status.json",
        result,
    )
    return result
