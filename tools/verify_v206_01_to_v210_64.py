import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from risk_engine_v2.engine import evaluate
r=evaluate(ROOT)
checks={
"stage":r["stage"]=="V210.64",
"status":r["status"]=="PASS",
"allowed_state":r["state"] in {"RISK_ENGINE_V2_READY","RISK_ENGINE_V2_HARD_BLOCKED"},
"execution_not_authorized":r["execution_authorized"] is False,
"broker_write_disabled":r["broker_write_enabled"] is False,
"live_submission_disabled":r["live_submission_enabled"] is False,
"live_orders_zero":r["actual_live_orders_submitted"]==0,
"web_api_present":(ROOT/"web_controller/risk_v2_api.py").exists(),
}
failed=[k for k,v in checks.items() if not v]
result={
 "verification_stage":"V210.64",
 "verification_status":"PASS" if not failed else "FAIL",
 "state":r["state"],
 "risk_gate":r["risk_gate"],
 "kill_switch":r["kill_switch"],
 "actual_live_orders_submitted":0,
 "checks":checks,"failed":failed
}
print(json.dumps(result,indent=2,sort_keys=True))
out=ROOT/"release/v206_01_to_v210_64/actual/risk_engine_v2_verification.json"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
raise SystemExit(0 if not failed else 1)
