import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/"release/v92_01_to_v92_32/actual/ai_explainability_pro_result.json"
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result=json.loads(path.read_text())
checks={
"stage":result.get("stage_range")=="V92.01-V92.32",
"status":result.get("status")=="PASS",
"allowed_state":result.get("state") in {
"AI_EXPLAINABILITY_SOURCE_REQUIRED",
"AI_EXPLAINABILITY_PRO_READY",
},
"hash_valid":(
    len(result.get("explanation_sha256",""))==64
    if result.get("state")=="AI_EXPLAINABILITY_PRO_READY"
    else True
),
"reasons_valid":isinstance(result.get("selection_reasons",[]),list),
"risks_valid":isinstance(result.get("risk_factors",[]),list),
"paper_only":result.get("paper_only") is True,
"broker_write_disabled":result.get("broker_write_enabled") is False,
"orders_disabled":result.get("order_submission_enabled") is False,
"live_disabled":result.get("live_trading_enabled") is False,
"network_disabled":result.get("external_network_enabled") is False,
}
failed=[name for name,passed in checks.items() if not passed]
print(json.dumps({
"verification_stage":"V92.32",
"verification_status":"PASS" if not failed else "FAIL",
"state":result.get("state"),
"strategy_id":result.get("strategy_id"),
"decision":result.get("decision"),
"confidence":result.get("confidence"),
"selection_reason_count":len(result.get("selection_reasons",[])),
"risk_factor_count":len(result.get("risk_factors",[])),
"checks":checks,
"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
