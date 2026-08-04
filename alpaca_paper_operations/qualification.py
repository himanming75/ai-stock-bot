from __future__ import annotations
from typing import Any

def evaluate_qualification(
    operation_rows:list[dict[str,Any]],
    policy:dict[str,Any],
)->dict[str,Any]:
    completed=len(operation_rows)
    critical_errors=sum(int(r.get("critical_error_count",0)) for r in operation_rows)
    reconciliation_failures=sum(
        1 for r in operation_rows if r.get("reconciliation_passed") is False
    )
    daily_loss_breaches=sum(
        1 for r in operation_rows if r.get("daily_loss_limit_breached") is True
    )
    checks={
        "minimum_sessions":completed>=int(policy.get("minimum_qualification_sessions",20)),
        "critical_errors_zero":critical_errors==0,
        "reconciliation_failures_zero":reconciliation_failures==0,
        "daily_loss_breaches_zero":daily_loss_breaches==0,
    }
    failed=[k for k,v in checks.items() if not v]
    return {
        "passed":not failed,
        "checks":checks,
        "failed":failed,
        "completed_sessions":completed,
        "critical_error_count":critical_errors,
        "reconciliation_failure_count":reconciliation_failures,
        "daily_loss_breach_count":daily_loss_breaches,
        "live_transition_authorized":False,
    }
