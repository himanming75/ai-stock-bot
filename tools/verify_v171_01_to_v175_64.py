import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from controlled_micro_live.engine import evaluate
r=evaluate(ROOT)
checks={
"stage":r["stage"]=="V175.64",
"status":r["status"]=="PASS",
"allowed_state":r["state"] in {"CONTROLLED_MICRO_LIVE_DRY_RUN_READY","CONTROLLED_MICRO_LIVE_HARD_BLOCKED"},
"execution_not_ready":r["micro_live_execution_ready"] is False,
"execution_not_authorized":r["execution_authorized"] is False,
"network_disabled":r["live_network_enabled"] is False,
"write_disabled":r["live_write_enabled"] is False,
"submission_disabled":r["live_submission_enabled"] is False,
"network_not_attempted":r["actual_live_network_attempted"] is False,
"write_not_attempted":r["actual_live_write_attempted"] is False,
"live_orders_zero":r["actual_live_orders_submitted"]==0,
"web_api_present":(ROOT/"web_controller/micro_live_api.py").exists(),
}
failed=[k for k,v in checks.items() if not v]
result={
"verification_stage":"V175.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":r["state"],
"readiness_gate":r["readiness_gate"],
"kill_switch":r["kill_switch"],
"dry_run_receipt":r["dry_run_receipt"],
"broker_reconciliation_plan":r["broker_reconciliation_plan"],
"actual_live_orders_submitted":0,
"checks":checks,"failed":failed,
}
print(json.dumps(result,indent=2,sort_keys=True))
out=ROOT/"release/v171_01_to_v175_64/actual/controlled_micro_live_verification.json"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
raise SystemExit(0 if not failed else 1)
