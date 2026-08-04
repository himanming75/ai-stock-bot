import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from live_approval.engine import evaluate
r=evaluate(ROOT)
checks={
"stage":r["stage"]=="V170.64",
"status":r["status"]=="PASS",
"allowed_state":r["state"] in {"LIVE_READ_ONLY_APPROVAL_READY","LIVE_READ_ONLY_APPROVAL_BLOCKED"},
"network_not_attempted":r["actual_live_network_attempted"] is False,
"write_not_attempted":r["actual_live_write_attempted"] is False,
"execution_not_authorized":r["execution_authorized"] is False,
"live_submission_disabled":r["live_submission_enabled"] is False,
"live_orders_zero":r["actual_live_orders_submitted"]==0,
"web_api_present":(ROOT/"web_controller/live_approval_api.py").exists(),
}
failed=[k for k,v in checks.items() if not v]
result={"verification_stage":"V170.64","verification_status":"PASS" if not failed else "FAIL","state":r["state"],"qualification_passed":r["qualification_passed"],"credentials":r["credentials"],"comparison":r["paper_live_comparison"],"approval_request":r["approval_request"],"actual_live_orders_submitted":0,"checks":checks,"failed":failed}
print(json.dumps(result,indent=2,sort_keys=True))
out=ROOT/"release/v166_01_to_v170_64/actual/live_approval_verification.json";out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
raise SystemExit(0 if not failed else 1)
