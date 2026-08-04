from __future__ import annotations
from typing import Any

def detect_anomalies(
    policy: dict[str, Any],
    telemetry: dict[str, Any],
) -> dict[str, Any]:
    events=[]
    if float(telemetry.get("price_gap_pct",0.0)) > float(
        policy.get("maximum_price_gap_pct",8.0)
    ):
        events.append("EXCESSIVE_PRICE_GAP")
    if float(telemetry.get("spread_pct",0.0)) > float(
        policy.get("maximum_spread_pct",2.0)
    ):
        events.append("EXCESSIVE_SPREAD")
    if int(telemetry.get("reject_count",0)) > int(
        policy.get("maximum_reject_count",3)
    ):
        events.append("EXCESSIVE_ORDER_REJECTS")
    if int(telemetry.get("duplicate_event_count",0)) > 0:
        events.append("DUPLICATE_EVENT_DETECTED")
    if telemetry.get("position_mismatch_detected") is True:
        events.append("POSITION_MISMATCH")
    return {
        "detected":bool(events),
        "event_count":len(events),
        "events":events,
        "passed":not events,
    }
