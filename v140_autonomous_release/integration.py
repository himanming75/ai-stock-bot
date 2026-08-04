from __future__ import annotations
from pathlib import Path
from typing import Any
from v140_autonomous_release.io import load_json

SOURCES={
"v121_123":"release/v121_01_to_v123_64/actual/alpaca_paper_operations_result.json",
"v124_126":"release/v124_01_to_v126_64/actual/continuous_paper_shadow_result.json",
"v127_128":"release/v127_01_to_v128_64/actual/micro_live_readiness_result.json",
"v129_130":"release/v129_01_to_v130_64/actual/restricted_live_candidate_result.json",
"v131_133":"release/v131_01_to_v133_64/actual/controlled_micro_live_result.json",
"v134_136":"release/v134_01_to_v136_64/actual/dynamic_live_risk_result.json",
"v137_139":"release/v137_01_to_v139_64/actual/autonomous_orchestrator_result.json",
}

def collect(root:Path)->dict[str,Any]:
    return {name:load_json(root/path) for name,path in SOURCES.items()}

def summarize(sources:dict[str,Any])->dict[str,Any]:
    return {
        name:{
            "present":bool(value),
            "stage":value.get("stage"),
            "state":value.get("state"),
            "status":value.get("status"),
            "actual_live_orders_submitted":value.get("actual_live_orders_submitted",0),
        }
        for name,value in sources.items()
    }
