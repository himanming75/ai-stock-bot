from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from production_operations.io import write_json,append_jsonl
from production_operations.reporting import build as build_reports
from production_operations.health import evaluate as evaluate_health
from production_operations.backup import create_snapshot,restore_plan
from production_operations.certificate import build as build_certificate

def evaluate(root:Path,create_backup:bool=True)->dict[str,Any]:
    report=build_reports(root)
    health=evaluate_health(root)
    backup=create_snapshot(root) if create_backup else {"file_count":0,"skipped":True}
    restore=restore_plan(root)
    certificate=build_certificate(root,report,health,backup)
    state="PRODUCTION_OPERATIONS_READY" if health["status"]=="HEALTHY" else "PRODUCTION_OPERATIONS_REVIEW_REQUIRED"
    observed=datetime.now(timezone.utc).isoformat()
    result={
        "stage":"V190.64",
        "state":state,
        "status":"PASS",
        "observed_at":observed,
        "reports":report,
        "health":health,
        "backup":backup,
        "restore_plan":restore,
        "operations_certificate":certificate,
        "reporting_ready":True,
        "backup_foundation_ready":True,
        "automatic_restore_enabled":False,
        "broker_write_enabled":False,
        "live_submission_enabled":False,
        "actual_live_orders_submitted":0,
        "next_phase":"V191_01_TO_V195_64_PRODUCTION_SCHEDULER_AUTOMATION",
    }
    actual=root/"release/v186_01_to_v190_64/actual"
    write_json(actual/"production_operations_result.json",result)
    append_jsonl(actual/"production_operations_ledger.jsonl",{
        "observed_at":observed,"state":state,
        "health_status":health["status"],
        "backup_id":backup.get("backup_id"),
        "actual_live_orders_submitted":0,
    })
    return result
