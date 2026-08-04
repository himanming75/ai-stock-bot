from __future__ import annotations
from typing import Any

def build_resume_gate(
    emergency: dict[str, Any],
    telemetry: dict[str, Any],
) -> dict[str, Any]:
    checks={
        "emergency_not_active":not emergency.get(
            "emergency_shutdown_required",False
        ),
        "manual_resume_approval_required":True,
        "manual_resume_approval_not_granted":telemetry.get(
            "manual_resume_approval_granted",False
        ) is False,
        "broker_healthy":telemetry.get("broker_health")=="HEALTHY",
        "market_data_fresh":float(
            telemetry.get("market_data_age_seconds",0.0)
        )<=30.0,
    }
    resume_allowed=(
        checks["emergency_not_active"]
        and checks["broker_healthy"]
        and checks["market_data_fresh"]
        and telemetry.get("manual_resume_approval_granted",False) is True
    )
    return {
        "checks":checks,
        "manual_resume_approval_required":True,
        "manual_resume_approval_granted":telemetry.get(
            "manual_resume_approval_granted",False
        ) is True,
        "resume_allowed":resume_allowed,
        "state":"RESUME_AUTHORIZED" if resume_allowed else "RESUME_BLOCKED",
    }
