from __future__ import annotations
from typing import Any

def evaluate_kill_switch(
    policy: dict[str, Any],
    telemetry: dict[str, Any],
) -> dict[str, Any]:
    reasons=[]
    if telemetry.get("manual_kill_switch") is True:
        reasons.append("MANUAL_KILL_SWITCH")
    if telemetry.get("broker_health") != "HEALTHY":
        reasons.append("BROKER_UNHEALTHY")
    if float(telemetry.get("market_data_age_seconds",0.0)) > float(
        policy.get("maximum_market_data_age_seconds",30.0)
    ):
        reasons.append("STALE_MARKET_DATA")
    if telemetry.get("market_halt_detected") is True:
        reasons.append("MARKET_HALT")
    if telemetry.get("clock_drift_seconds",0.0) > float(
        policy.get("maximum_clock_drift_seconds",5.0)
    ):
        reasons.append("CLOCK_DRIFT")
    return {
        "triggered":bool(reasons),
        "reasons":reasons,
        "state":"KILL_SWITCH_TRIGGERED" if reasons else "ARMED_NOT_TRIGGERED",
    }
