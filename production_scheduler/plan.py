from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from production_scheduler.config import load
from production_scheduler.io import write_json

def build(root:Path)->dict:
    c=load(root)
    jobs=[
        {"job":"pre_market","enabled":c["pre_market_enabled"],"time":c["pre_market_time"]},
        {"job":"market_open_health","enabled":c["market_open_health_enabled"],"time":c["market_open_health_time"]},
        {"job":"qualification_refresh","enabled":c["qualification_refresh_enabled"],"time":c["qualification_refresh_time"]},
        {"job":"portfolio_refresh","enabled":c["portfolio_refresh_enabled"],"time":c["portfolio_refresh_time"]},
        {"job":"post_market_report","enabled":c["post_market_report_enabled"],"time":c["post_market_report_time"]},
        {"job":"nightly_backup","enabled":c["nightly_backup_enabled"],"time":c["nightly_backup_time"]},
    ]
    result={
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "scheduler_enabled":c["enabled"],
        "timezone":c["timezone"],
        "jobs":jobs,
        "enabled_job_count":sum(1 for x in jobs if x["enabled"]),
        "scheduled_order_submission_included":False,
        "broker_write_enabled":False,
        "actual_live_orders_submitted":0,
    }
    write_json(root/"release/v191_01_to_v195_64/actual/scheduler_plan.json",result)
    return result
