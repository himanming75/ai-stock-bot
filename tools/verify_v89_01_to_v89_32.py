import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"release/v89_01_to_v89_32/actual/v89_result.json"
if not p.exists(): raise SystemExit("RESULT NOT FOUND")
r=json.loads(p.read_text())
checks={
"stage":r.get("stage_range")=="V89.01-V89.32","status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {"HISTORICAL_DATA_REQUIRED","STRATEGY_CHAMPION_CANDIDATE_READY","STRATEGY_PERFORMANCE_REVIEW_REQUIRED"},
"paper_only":r.get("paper_only") is True,"broker_write_disabled":r.get("broker_write_enabled") is False,
"orders_disabled":r.get("order_submission_enabled") is False,"live_disabled":r.get("live_trading_enabled") is False,
"network_disabled":r.get("external_network_enabled") is False,
"final_validation_present":bool(r.get("final_validation"))
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"verification_stage":"V89.32","verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),"checks":checks,"failed":failed},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
