import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"release/v91_01_to_v91_32/actual/ultimate_strategy_lab_result.json"
if not p.exists():raise SystemExit("RESULT NOT FOUND")
r=json.loads(p.read_text())
checks={
"stage":r.get("stage_range")=="V91.01-V91.32",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {
"STRATEGY_LAB_HISTORICAL_DATA_REQUIRED",
"ULTIMATE_STRATEGY_LAB_CHAMPION_READY",
"ULTIMATE_STRATEGY_LAB_REVIEW_REQUIRED"},
"registry_present":len(r.get("registry",[]))>=10,
"rankings_valid":isinstance(r.get("rankings",[]),list),
"paper_only":r.get("paper_only") is True,
"broker_write_disabled":r.get("broker_write_enabled") is False,
"orders_disabled":r.get("order_submission_enabled") is False,
"live_disabled":r.get("live_trading_enabled") is False,
"network_disabled":r.get("external_network_enabled") is False,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
"verification_stage":"V91.32",
"verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),
"registered_strategy_count":r.get("registered_strategy_count",len(r.get("registry",[]))),
"executed_strategy_count":r.get("executed_strategy_count",0),
"approved_strategy_count":r.get("approved_strategy_count",0),
"champion":r.get("champion",{}).get("strategy_name") if r.get("champion") else None,
"checks":checks,"failed":failed},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
