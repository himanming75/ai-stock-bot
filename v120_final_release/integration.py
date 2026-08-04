from __future__ import annotations
from pathlib import Path
from typing import Any
from v120_final_release.io import load_json

STAGES = [
    ("V105_FINAL_RELEASE",
     "release/v105_33_to_v105_64/actual/production_readiness_final_release_result.json",
     {"PRODUCTION_READINESS_FINAL_RELEASE_COMPLETE"}),
    ("V106_DAILY_RUNNER",
     "release/v106_01_to_v106_32/actual/daily_paper_runner_result.json",
     {"DAILY_PAPER_TRADING_RUN_COMPLETED","DAILY_PAPER_TRADING_DUPLICATE_RUN_BLOCKED"}),
    ("V108_FAST_TRACK_A",
     "release/v106_33_to_v108_64/actual/fast_track_paper_result.json",
     {"FAST_TRACK_PAPER_EXECUTION_AND_ANALYTICS_COMPLETE","FAST_TRACK_PAPER_CYCLE_DUPLICATE_BLOCKED"}),
    ("V110_FAST_TRACK_B",
     "release/v109_01_to_v110_64/actual/autonomous_paper_operations_result.json",
     {"AUTONOMOUS_PAPER_OPERATIONS_READY"}),
    ("V113_READ_ONLY_BROKER",
     "release/v111_01_to_v113_64/actual/live_broker_readonly_result.json",
     {"LIVE_BROKER_READ_ONLY_INFRASTRUCTURE_READY"}),
    ("V116_SAFE_EXECUTION",
     "release/v114_01_to_v116_64/actual/broker_safe_execution_result.json",
     {"BROKER_INTEGRATION_SAFE_EXECUTION_BOUNDARY_READY"}),
    ("V119_LIVE_SAFETY",
     "release/v117_01_to_v119_64/actual/live_safety_system_result.json",
     {"LIVE_SAFETY_SYSTEM_READY"}),
]

def evaluate_stages(root: Path) -> dict[str, Any]:
    rows=[]
    for name,rel,allowed in STAGES:
        value=load_json(root/rel)
        state=value.get("state")
        rows.append({
            "name":name,
            "path":rel,
            "state":state,
            "status":value.get("status"),
            "ready":state in allowed and value.get("status")=="PASS",
            "actual_orders_submitted":value.get("actual_orders_submitted",0),
            "paper_only":value.get("paper_only",True),
        })
    return {
        "stage_count":len(rows),
        "ready_stage_count":sum(1 for r in rows if r["ready"]),
        "rows":rows,
        "passed":all(r["ready"] for r in rows),
    }
