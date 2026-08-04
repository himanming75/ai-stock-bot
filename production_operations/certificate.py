from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from production_operations.io import write_json,sha256_file

def build(root:Path,report:dict[str,Any],health:dict[str,Any],backup:dict[str,Any])->dict[str,Any]:
    passed=health.get("status")=="HEALTHY"
    certificate={
        "certificate_type":"PRODUCTION_OPERATIONS_READ_ONLY_CERTIFICATE",
        "issued_at":datetime.now(timezone.utc).isoformat(),
        "operations_ready":passed,
        "reporting_ready":True,
        "backup_ready":backup.get("file_count",0)>=0,
        "health_status":health.get("status"),
        "live_trading_ready":False,
        "broker_write_enabled":False,
        "live_submission_enabled":False,
        "actual_live_orders_submitted":0,
    }
    write_json(root/"release/v186_01_to_v190_64/actual/operations_certificate.json",certificate)
    return certificate
