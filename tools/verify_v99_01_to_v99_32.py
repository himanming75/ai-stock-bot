import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/"release/v99_01_to_v99_32/actual/ai_portfolio_manager_result.json"
if not path.exists(): raise SystemExit("RESULT NOT FOUND")
r=json.loads(path.read_text())
checks={
"stage":r.get("stage_range")=="V99.01-V99.32",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {
"AI_PORTFOLIO_MANAGER_SOURCE_REQUIRED",
"AI_PORTFOLIO_MANAGER_READY",
"AI_PORTFOLIO_MANAGER_REVIEW_REQUIRED"},
"hash_valid":len(r.get("ai_portfolio_certificate_sha256",""))==64 if r.get("state")!="AI_PORTFOLIO_MANAGER_SOURCE_REQUIRED" else True,
"rankings_valid":isinstance(r.get("rankings",[]),list),
"allocation_valid":isinstance(r.get("allocation",{}),dict),
"risk_valid":isinstance(r.get("risk",{}),dict),
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
"verification_stage":"V99.32",
"verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),
"portfolio_id":r.get("portfolio_id"),
"candidate_count":r.get("candidate_count"),
"champion":r.get("champion"),
"allocation":r.get("allocation"),
"risk":r.get("risk"),
"checks":checks,"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
