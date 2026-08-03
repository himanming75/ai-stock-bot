import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"release/v89_33_to_v89_64/actual/portfolio_optimization_result.json"
if not p.exists(): raise SystemExit("RESULT NOT FOUND")
r=json.loads(p.read_text())
data=r.get("portfolio_optimization",{})
checks={
"stage":r.get("stage_range")=="V89.33-V89.64",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {
"PORTFOLIO_OPTIMIZATION_APPROVED",
"PORTFOLIO_OPTIMIZATION_REVIEW_REQUIRED",
"SOURCE_STRATEGY_RESULTS_REQUIRED"
},
"allocations_valid":(
    len(data.get("allocations",[]))>=1
    if r.get("state")!="SOURCE_STRATEGY_RESULTS_REQUIRED"
    else len(data.get("allocations",[]))==0
),
"risk_present":bool(data.get("risk")),
"paper_only":r.get("paper_only") is True,
"broker_write_disabled":r.get("broker_write_enabled") is False,
"orders_disabled":r.get("order_submission_enabled") is False,
"live_disabled":r.get("live_trading_enabled") is False,
"network_disabled":r.get("external_network_enabled") is False,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"verification_stage":"V89.64","verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),"checks":checks,"failed":failed},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
