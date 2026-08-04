import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=(
    ROOT/"release/v100_33_to_v100_64/actual/"
    "risk_budget_allocation_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

r=json.loads(path.read_text())
checks={
"stage":r.get("stage_range")=="V100.33-V100.64",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {
"RISK_BUDGET_SOURCE_REQUIRED",
"RISK_BUDGET_ALLOCATION_READY",
"RISK_BUDGET_ALLOCATION_REVIEW_REQUIRED"},
"hash_valid":(
    len(r.get("risk_budget_certificate_sha256",""))==64
    if r.get("state")!="RISK_BUDGET_SOURCE_REQUIRED"
    else True
),
"allocation_valid":isinstance(r.get("risk_budget_allocation",{}),dict),
"exposure_valid":isinstance(r.get("dynamic_exposure_control",{}),dict),
"heat_valid":isinstance(r.get("portfolio_heat",{}),dict),
"gate_valid":isinstance(r.get("risk_budget_gate",{}),dict),
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
failed=[name for name,passed in checks.items() if not passed]
print(json.dumps({
"verification_stage":"V100.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),
"risk_budget_id":r.get("risk_budget_id"),
"candidate_count":r.get("candidate_count"),
"risk_budget_allocation":r.get("risk_budget_allocation"),
"dynamic_exposure_control":r.get("dynamic_exposure_control"),
"portfolio_heat":r.get("portfolio_heat"),
"risk_budget_gate":r.get("risk_budget_gate"),
"checks":checks,
"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
