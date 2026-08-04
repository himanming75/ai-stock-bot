from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from final_production_release.io import load_json,write_json,sha256_file

STAGES=[
 ("V120_FINAL","release/v120_final/actual/v120_final_release_result.json"),
 ("V140_FINAL","release/v140_final/actual/v140_final_release_result.json"),
 ("V145_WEB","release/v141_01_to_v145_64/actual/web_controller_verification.json"),
 ("V155_PAPER_WEB","release/v151_01_to_v155_64/actual/paper_web_operations_verification.json"),
 ("V160_OPERATIONS","release/v156_01_to_v160_64/actual/operations_center_verification.json"),
 ("V165_QUALIFICATION","release/v161_01_to_v165_64/actual/paper_qualification_result.json"),
 ("V170_LIVE_APPROVAL","release/v166_01_to_v170_64/actual/live_read_only_approval_result.json"),
 ("V175_MICRO_LIVE","release/v171_01_to_v175_64/actual/controlled_micro_live_result.json"),
 ("V180_RESTRICTED_LIVE","release/v176_01_to_v180_64/actual/restricted_live_automation_result.json"),
 ("V185_PORTFOLIO","release/v181_01_to_v185_64/actual/portfolio_broker_result.json"),
 ("V190_OPERATIONS_REPORTING","release/v186_01_to_v190_64/actual/production_operations_result.json"),
 ("V195_SCHEDULER","release/v191_01_to_v195_64/actual/production_scheduler_result.json"),
 ("V200_MULTI_BROKER","release/v196_01_to_v200_64/actual/multi_broker_production_result.json"),
 ("V205_PLUGIN_FRAMEWORK","release/v201_01_to_v205_64/actual/broker_plugin_framework_result.json"),
 ("V210_RISK_V2","release/v206_01_to_v210_64/actual/risk_engine_v2_result.json"),
 ("V215_STRATEGY_ENSEMBLE","release/v211_01_to_v215_64/actual/ai_strategy_ensemble_result.json"),
]

def build(root:Path)->dict[str,Any]:
    rows=[]
    total_live_orders=0
    unsafe=[]
    for stage,rel in STAGES:
        path=root/rel
        payload=load_json(path)
        present=path.exists()
        live_orders=int(payload.get("actual_live_orders_submitted",0) or 0) if payload else 0
        total_live_orders+=live_orders
        flags={
          "broker_write_enabled":payload.get("broker_write_enabled"),
          "live_submission_enabled":payload.get("live_submission_enabled"),
          "execution_authorized":payload.get("execution_authorized"),
          "automatic_order_submission_enabled":payload.get("automatic_order_submission_enabled"),
        }
        unsafe_flags=[k for k,v in flags.items() if v is True]
        if unsafe_flags:unsafe.append({"stage":stage,"flags":unsafe_flags})
        rows.append({
          "stage":stage,"path":rel,"present":present,
          "state":payload.get("state","NOT_AVAILABLE"),
          "status":payload.get("status",payload.get("verification_status","NOT_AVAILABLE")),
          "actual_live_orders_submitted":live_orders,
          "unsafe_flags":unsafe_flags,
          "sha256":sha256_file(path) if present else None,
        })
    result={
      "generated_at":datetime.now(timezone.utc).isoformat(),
      "expected_stage_count":len(STAGES),
      "present_stage_count":sum(1 for x in rows if x["present"]),
      "missing_stages":[x["stage"] for x in rows if not x["present"]],
      "rows":rows,
      "unsafe_stage_flags":unsafe,
      "total_actual_live_orders_submitted":total_live_orders,
    }
    write_json(root/"release/v216_01_to_v220_64/actual/final_stage_inventory.json",result)
    return result
