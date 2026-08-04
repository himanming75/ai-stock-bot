from __future__ import annotations
from pathlib import Path
from continuous_autonomous_engine.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result=load_json(
        root/"release/v104_01_to_v104_32/actual/"
        "continuous_autonomous_engine_result.json"
    )
    return {
        "state":result.get("state","NOT_AVAILABLE"),
        "engine_id":result.get("engine_id"),
        "engine_action":result.get("engine_action"),
        "selected_session":result.get("selected_session",{}),
        "iteration_gates":result.get("iteration_gates",{}),
        "phases":result.get("phases",[]),
        "checkpoint":result.get("checkpoint",{}),
        "recovery":result.get("recovery",{}),
        "continuous_service_started":False,
        "execution_authorized":False,
        "paper_only":True,
    }
