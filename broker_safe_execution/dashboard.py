from __future__ import annotations
from pathlib import Path
from broker_safe_execution.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result=load_json(
        root/"release/v114_01_to_v116_64/actual/"
        "broker_safe_execution_result.json"
    )
    return {
        "state":result.get("state","NOT_AVAILABLE"),
        "selected_adapter":result.get("selected_adapter"),
        "intent_count":len(result.get("order_intents",[])),
        "validation":result.get("validation",{}),
        "execution_queue":result.get("execution_queue",{}),
        "manual_approval_package":result.get(
            "manual_approval_package",{}
        ),
        "safe_gateway":result.get("safe_gateway",{}),
        "actual_orders_submitted":0,
        "paper_only":True,
    }
