import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from production_operations.engine import evaluate
r=evaluate(ROOT,create_backup=False)
checks={
"stage":r["stage"]=="V190.64",
"status":r["status"]=="PASS",
"allowed_state":r["state"] in {"PRODUCTION_OPERATIONS_READY","PRODUCTION_OPERATIONS_REVIEW_REQUIRED"},
"reporting_ready":r["reporting_ready"] is True,
"backup_foundation_ready":r["backup_foundation_ready"] is True,
"automatic_restore_disabled":r["automatic_restore_enabled"] is False,
"broker_write_disabled":r["broker_write_enabled"] is False,
"live_submission_disabled":r["live_submission_enabled"] is False,
"live_orders_zero":r["actual_live_orders_submitted"]==0,
"web_api_present":(ROOT/"web_controller/production_api.py").exists(),
}
failed=[k for k,v in checks.items() if not v]
result={
"verification_stage":"V190.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":r["state"],
"health":r["health"],
"report_summary":{
 "daily":r["reports"]["daily"],
 "weekly":r["reports"]["weekly"],
 "monthly":r["reports"]["monthly"],
},
"operations_certificate":r["operations_certificate"],
"actual_live_orders_submitted":0,
"checks":checks,"failed":failed,
}
print(json.dumps(result,indent=2,sort_keys=True))
out=ROOT/"release/v186_01_to_v190_64/actual/production_operations_verification.json"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
raise SystemExit(0 if not failed else 1)
