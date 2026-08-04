import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from production_scheduler.engine import evaluate
r=evaluate(ROOT)
checks={
"stage":r["stage"]=="V195.64",
"status":r["status"]=="PASS",
"allowed_state":r["state"] in {"PRODUCTION_SCHEDULER_READY","PRODUCTION_SCHEDULER_REVIEW_REQUIRED"},
"windows_scheduler_ready":r["windows_task_scheduler_ready"] is True,
"retry_ready":r["retry_foundation_ready"] is True,
"duplicate_guard_ready":r["duplicate_execution_guard_ready"] is True,
"automatic_order_submission_disabled":r["automatic_order_submission_enabled"] is False,
"broker_write_disabled":r["broker_write_enabled"] is False,
"live_submission_disabled":r["live_submission_enabled"] is False,
"live_orders_zero":r["actual_live_orders_submitted"]==0,
"web_api_present":(ROOT/"web_controller/production_scheduler_api.py").exists(),
}
failed=[k for k,v in checks.items() if not v]
result={
"verification_stage":"V195.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":r["state"],
"scheduler_plan":r["scheduler_plan"],
"actual_live_orders_submitted":0,
"checks":checks,"failed":failed,
}
print(json.dumps(result,indent=2,sort_keys=True))
out=ROOT/"release/v191_01_to_v195_64/actual/production_scheduler_verification.json"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
raise SystemExit(0 if not failed else 1)
