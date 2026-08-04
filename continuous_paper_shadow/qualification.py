from __future__ import annotations
from typing import Any

def evaluate(rows:list[dict[str,Any]],policy:dict[str,Any])->dict[str,Any]:
    sessions=len(rows)
    critical=sum(int(r.get("critical_error_count",0)) for r in rows)
    recon_fail=sum(1 for r in rows if r.get("reconciliation_passed") is False)
    live_orders=sum(int(r.get("actual_live_orders_submitted",0)) for r in rows)
    checks={
        "minimum_sessions":sessions>=int(policy.get("minimum_sessions",20)),
        "critical_errors_zero":critical==0,
        "reconciliation_failures_zero":recon_fail==0,
        "live_orders_zero":live_orders==0,
    }
    failed=[k for k,v in checks.items() if not v]
    return {
        "passed":not failed,"checks":checks,"failed":failed,
        "completed_sessions":sessions,"critical_error_count":critical,
        "reconciliation_failure_count":recon_fail,
        "actual_live_orders_submitted":live_orders,
        "micro_live_authorized":False,
    }
