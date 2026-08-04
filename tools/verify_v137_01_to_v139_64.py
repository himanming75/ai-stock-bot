import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"release/v137_01_to_v139_64/actual/autonomous_orchestrator_result.json"
if not p.exists(): raise SystemExit("RESULT NOT FOUND")
r=json.loads(p.read_text())
checks={
"stage":r.get("stage_range")=="V137.01-V139.64",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {
"AUTONOMOUS_PAPER_TRADING_CYCLE_COMPLETE",
"AUTONOMOUS_TRADING_MARKET_CLOSED",
"AUTONOMOUS_TRADING_NO_SIGNAL",
"AUTONOMOUS_TRADING_RISK_BLOCKED",
"AUTONOMOUS_TRADING_DUPLICATE_CYCLE_BLOCKED",
"AUTONOMOUS_TRADING_READY_NO_EXECUTION",
"AUTONOMOUS_ORCHESTRATOR_SOURCE_REQUIRED"},
"hash_valid":len(r.get("result_sha256",""))==64,
"paper_only":r.get("paper_only",True) is True,
"live_network_disabled":r.get("live_network_enabled",False) is False,
"live_submission_disabled":r.get("live_submission_enabled",False) is False,
"network_not_attempted":r.get("real_live_network_attempted",False) is False,
"submission_not_attempted":r.get("real_live_submission_attempted",False) is False,
"live_orders_zero":r.get("actual_live_orders_submitted",0)==0,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
"verification_stage":"V139.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),
"market":r.get("market"),
"signals":r.get("signals"),
"selected_candidates":r.get("selected_candidates"),
"paper_order_plans":r.get("paper_order_plans"),
"paper_execution":r.get("paper_execution"),
"positions":r.get("positions"),
"performance":r.get("performance"),
"checkpoint":r.get("checkpoint"),
"actual_paper_orders_submitted":r.get("actual_paper_orders_submitted"),
"actual_live_orders_submitted":r.get("actual_live_orders_submitted"),
"checks":checks,"failed":failed,
},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
