import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"release/v95_01_to_v95_32/actual/paper_execution_simulation_result.json"
if not p.exists(): raise SystemExit("RESULT NOT FOUND")
r=json.loads(p.read_text())
checks={
"stage":r.get("stage_range")=="V95.01-V95.32",
"status":r.get("status")=="PASS",
"allowed_state":r.get("state") in {
"PAPER_EXECUTION_SIMULATOR_SOURCE_REQUIRED",
"PAPER_EXECUTION_SIMULATION_COMPLETED",
"PAPER_EXECUTION_SIMULATION_DUPLICATE_CYCLE_BLOCKED"},
"hash_valid":len(r.get("paper_simulation_certificate_sha256",""))==64 if r.get("state")!="PAPER_EXECUTION_SIMULATOR_SOURCE_REQUIRED" else True,
"fills_valid":isinstance(r.get("fills",[]),list),
"orders_zero":r.get("actual_orders_submitted")==0,
"paper_only":r.get("paper_only") is True,
"broker_write_disabled":r.get("broker_write_enabled") is False,
"orders_disabled":r.get("order_submission_enabled") is False,
"live_disabled":r.get("live_trading_enabled") is False,
"network_disabled":r.get("external_network_enabled") is False,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
"verification_stage":"V95.32",
"verification_status":"PASS" if not failed else "FAIL",
"state":r.get("state"),
"simulation_date":r.get("simulation_date"),
"cycle_id":r.get("cycle_id"),
"duplicate_cycle":r.get("duplicate_cycle"),
"fill_summary":r.get("fill_summary",{}),
"ending_cash":r.get("ending_cash"),
"ending_equity":r.get("ending_equity"),
"checks":checks,"failed":failed},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
