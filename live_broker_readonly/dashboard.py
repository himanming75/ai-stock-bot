from __future__ import annotations
from pathlib import Path
from live_broker_readonly.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result=load_json(
        root/"release/v111_01_to_v113_64/actual/"
        "live_broker_readonly_result.json"
    )
    return {
        "state":result.get("state","NOT_AVAILABLE"),
        "selected_adapter":result.get("selected_adapter"),
        "adapter_health":result.get("adapter_health",{}),
        "account_snapshot":result.get("account_snapshot",{}),
        "position_count":len(result.get("position_snapshot",[])),
        "order_count":len(result.get("order_snapshot",[])),
        "drift":result.get("drift",{}),
        "read_only":True,
        "real_network_connection_attempted":False,
        "actual_orders_submitted":0,
    }
