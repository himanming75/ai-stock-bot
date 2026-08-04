import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from paper_qualification.engine import evaluate
r=evaluate(ROOT)
checks={
"stage":r["stage"]=="V165.64",
"status":r["status"]=="PASS",
"allowed_state":r["state"] in {"PAPER_QUALIFICATION_PASSED","PAPER_QUALIFICATION_IN_PROGRESS"},
"paper_only":r["paper_only"] is True,
"live_not_ready":r["live_trading_ready"] is False,
"live_disabled":r["live_submission_enabled"] is False,
"live_orders_zero":r["actual_live_orders_submitted"]==0,
"qualification_api_present":(ROOT/"web_controller/qualification_api.py").exists(),
}
failed=[k for k,v in checks.items() if not v]
result={"verification_stage":"V165.64","verification_status":"PASS" if not failed else "FAIL","state":r["state"],"metrics":r["metrics"],"qualification":r["qualification"],"recommendation":r["recommendation"],"actual_live_orders_submitted":0,"checks":checks,"failed":failed}
print(json.dumps(result,indent=2,sort_keys=True))
out=ROOT/"release/v161_01_to_v165_64/actual/paper_qualification_verification.json";out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
raise SystemExit(0 if not failed else 1)
