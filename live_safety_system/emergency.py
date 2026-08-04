from __future__ import annotations
from typing import Any

def build_emergency_action(
    kill_switch: dict[str, Any],
    loss_limits: dict[str, Any],
    exposure: dict[str, Any],
    anomaly: dict[str, Any],
) -> dict[str, Any]:
    triggers=[]
    if kill_switch.get("triggered"):
        triggers.extend(kill_switch.get("reasons",[]))
    if not loss_limits.get("passed"):
        triggers.extend(loss_limits.get("failed",[]))
    if not exposure.get("passed"):
        triggers.extend(exposure.get("failed",[]))
    if anomaly.get("detected"):
        triggers.extend(anomaly.get("events",[]))
    shutdown=bool(triggers)
    return {
        "emergency_shutdown_required":shutdown,
        "triggers":sorted(set(triggers)),
        "cancel_open_orders_requested":shutdown,
        "flatten_positions_requested":False,
        "cancel_requests_executed":0,
        "flatten_requests_executed":0,
        "broker_writes_executed":0,
        "state":"EMERGENCY_STOP_REQUIRED" if shutdown else "SAFETY_CLEAR",
    }
