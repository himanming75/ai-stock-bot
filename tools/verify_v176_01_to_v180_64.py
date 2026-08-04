import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from restricted_live_automation.engine import evaluate
r=evaluate(ROOT)
checks={
 "stage":r["stage"]=="V180.64",
 "status":r["status"]=="PASS",
 "allowed_state":r["state"] in {"RESTRICTED_LIVE_AUTOMATION_DRY_RUN_READY","RESTRICTED_LIVE_AUTOMATION_HARD_BLOCKED"},
 "execution_not_authorized":r["execution_authorized"] is False,
 "automatic_submission_disabled":r["automatic_submission_enabled"] is False,
 "network_disabled":r["live_network_enabled"] is False,
 "write_disabled":r["live_write_enabled"] is False,
 "submission_disabled":r["live_submission_enabled"] is False,
 "network_not_attempted":r["actual_live_network_attempted"] is False,
 "write_not_attempted":r["actual_live_write_attempted"] is False,
 "live_orders_zero":r["actual_live_orders_submitted"]==0,
 "web_api_present":(ROOT/"web_controller/restricted_live_api.py").exists()
}
failed=[k for k,v in checks.items() if not v]
result={
 "verification_stage":"V180.64",
 "verification_status":"PASS" if not failed else "FAIL",
 "state":r["state"],
 "restricted_gate":r["restricted_gate"],
 "automation_plan":r["automation_plan"],
 "actual_live_orders_submitted":0,
 "checks":checks,"failed":failed
}
print(json.dumps(result,indent=2,sort_keys=True))
out=ROOT/"release/v176_01_to_v180_64/actual/restricted_live_automation_verification.json"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
raise SystemExit(0 if not failed else 1)
