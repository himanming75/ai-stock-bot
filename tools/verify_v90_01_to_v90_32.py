import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"release/v90_01_to_v90_32/actual/dashboard_analytics_v3_state.json"
if not p.exists():raise SystemExit("STATE NOT FOUND")
r=json.loads(p.read_text())
checks={
"stage":r.get("stage_range")=="V90.01-V90.32",
"state":r.get("state")=="DASHBOARD_ANALYTICS_V3_READY",
"status":r.get("status")=="PASS",
"strategy_rows":isinstance(r.get("strategy_rows"),list),
"allocations":isinstance(r.get("allocations"),list),
"alerts":isinstance(r.get("alerts"),list),
"validation":isinstance(r.get("validation_progress"),dict),
"paper_only":r.get("paper_only") is True,
"broker_write_disabled":r.get("broker_write_enabled") is False,
"orders_disabled":r.get("order_submission_enabled") is False,
"live_disabled":r.get("live_trading_enabled") is False,
"network_disabled":r.get("external_network_enabled") is False,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"verification_stage":"V90.32","verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),"strategy_count":len(r.get("strategy_rows",[])),
"allocation_count":len(r.get("allocations",[])),"alert_count":len(r.get("alerts",[])),
"checks":checks,"failed":failed},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
