import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from ai_strategy_ensemble.engine import evaluate
r=evaluate(ROOT)
checks={
"stage":r["stage"]=="V215.64",
"status":r["status"]=="PASS",
"allowed_state":r["state"] in {"AI_STRATEGY_ENSEMBLE_READY","AI_STRATEGY_ENSEMBLE_REVIEW_REQUIRED"},
"rankings_present":bool(r["rankings"]),
"allocations_present":bool(r["allocations"]),
"promotion_not_authorized":r["strategy_promotion_authorized"] is False,
"execution_not_authorized":r["execution_authorized"] is False,
"automatic_submission_disabled":r["automatic_order_submission_enabled"] is False,
"broker_write_disabled":r["broker_write_enabled"] is False,
"live_submission_disabled":r["live_submission_enabled"] is False,
"live_orders_zero":r["actual_live_orders_submitted"]==0,
"web_api_present":(ROOT/"web_controller/strategy_ensemble_api.py").exists(),
}
failed=[k for k,v in checks.items() if not v]
result={
"verification_stage":"V215.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":r["state"],
"champion":r["champion"],
"rankings":r["rankings"],
"allocations":r["allocations"],
"ensemble_signal":r["ensemble_signal"],
"risk_gate_passed":r["risk_gate_passed"],
"actual_live_orders_submitted":0,
"checks":checks,"failed":failed,
}
print(json.dumps(result,indent=2,sort_keys=True))
out=ROOT/"release/v211_01_to_v215_64/actual/ai_strategy_ensemble_verification.json"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
raise SystemExit(0 if not failed else 1)
