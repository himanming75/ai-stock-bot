import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=(
    ROOT/"release/v100_01_to_v100_32/actual/"
    "ai_risk_manager_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

r=json.loads(path.read_text())
checks={
"stage":r.get("stage_range")=="V100.01-V100.32",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {
"AI_RISK_MANAGER_SOURCE_REQUIRED",
"AI_RISK_MANAGER_READY",
"AI_RISK_MANAGER_REVIEW_REQUIRED"},
"hash_valid":(
    len(r.get("ai_risk_manager_certificate_sha256",""))==64
    if r.get("state")!="AI_RISK_MANAGER_SOURCE_REQUIRED"
    else True
),
"exposure_valid":isinstance(r.get("exposure",{}),dict),
"var_valid":isinstance(r.get("value_at_risk",{}),dict),
"stress_valid":isinstance(r.get("stress",{}),dict),
"score_valid":isinstance(r.get("risk_score",{}),dict),
"gate_valid":isinstance(r.get("pre_execution_gate",{}),dict),
"execution_not_authorized":r.get("execution_authorized") is False,
"manual_approval_required":r.get("manual_approval_required") is True,
"credentials_unused":r.get("actual_credentials_used") is False,
"network_unused":r.get("actual_external_network_used") is False,
"orders_zero":r.get("actual_orders_submitted")==0,
"paper_only":r.get("paper_only") is True,
"broker_write_disabled":r.get("broker_write_enabled") is False,
"orders_disabled":r.get("order_submission_enabled") is False,
"live_disabled":r.get("live_trading_enabled") is False,
"network_disabled":r.get("external_network_enabled") is False,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
"verification_stage":"V100.32",
"verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),
"risk_assessment_id":r.get("risk_assessment_id"),
"account_equity":r.get("account_equity"),
"exposure":r.get("exposure"),
"value_at_risk":r.get("value_at_risk"),
"drawdown":r.get("drawdown"),
"stress":r.get("stress"),
"risk_score":r.get("risk_score"),
"pre_execution_gate":r.get("pre_execution_gate"),
"checks":checks,
"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
