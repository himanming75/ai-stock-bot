from __future__ import annotations
from pathlib import Path
from live_safety_system.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result=load_json(
        root/"release/v117_01_to_v119_64/actual/"
        "live_safety_system_result.json"
    )
    return {
        "state":result.get("state","NOT_AVAILABLE"),
        "safety_assessment_id":result.get("safety_assessment_id"),
        "safety_passed":result.get("safety_passed"),
        "kill_switch":result.get("kill_switch",{}),
        "loss_limits":result.get("loss_limits",{}),
        "exposure":result.get("exposure",{}),
        "anomaly_detection":result.get("anomaly_detection",{}),
        "emergency_action":result.get("emergency_action",{}),
        "resume_gate":result.get("resume_gate",{}),
        "actual_orders_submitted":0,
        "paper_only":True,
    }
