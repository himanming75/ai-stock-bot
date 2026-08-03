import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=(
    ROOT / "release/v99_33_to_v99_64/actual/"
    "portfolio_rebalance_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result=json.loads(path.read_text())
checks={
"stage":result.get("stage_range")=="V99.33-V99.64",
"status":result.get("status")=="PASS",
"allowed_state":result.get("state") in {
"PORTFOLIO_REBALANCE_SOURCE_REQUIRED",
"PORTFOLIO_REBALANCE_INTENTS_READY",
"PORTFOLIO_REBALANCE_NO_ACTION",
"PORTFOLIO_REBALANCE_REVIEW_REQUIRED",
},
"hash_valid":(
    len(result.get("portfolio_rebalance_certificate_sha256",""))==64
    if result.get("state")!="PORTFOLIO_REBALANCE_SOURCE_REQUIRED"
    else True
),
"weights_valid":isinstance(result.get("weight_comparison",[]),list),
"turnover_valid":isinstance(result.get("turnover",{}),dict),
"risk_valid":isinstance(result.get("risk",{}),dict),
"execution_not_authorized":result.get("execution_authorized") is False,
"manual_approval_required":result.get("manual_approval_required") is True,
"credentials_unused":result.get("actual_credentials_used") is False,
"network_unused":result.get("actual_external_network_used") is False,
"orders_zero":result.get("actual_orders_submitted")==0,
"paper_only":result.get("paper_only") is True,
"broker_write_disabled":result.get("broker_write_enabled") is False,
"orders_disabled":result.get("order_submission_enabled") is False,
"live_disabled":result.get("live_trading_enabled") is False,
"network_disabled":result.get("external_network_enabled") is False,
}
failed=[name for name,passed in checks.items() if not passed]
print(json.dumps({
"verification_stage":"V99.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":result.get("state"),
"rebalance_id":result.get("rebalance_id"),
"account_equity":result.get("account_equity"),
"weight_comparison":result.get("weight_comparison"),
"planned_intent_count":result.get("planned_intent_count"),
"actionable_intent_count":result.get("actionable_intent_count"),
"duplicate_intent_count":result.get("duplicate_intent_count"),
"turnover":result.get("turnover"),
"risk":result.get("risk"),
"checks":checks,
"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
