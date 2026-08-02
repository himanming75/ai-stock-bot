import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"release/op4_17_to_op4_20/actual/paper_pilot_automation_result.json"
if not p.exists():raise SystemExit("VERIFY=FAIL result missing")
r=json.loads(p.read_text(encoding="utf-8"))
checks={
"status":r.get("status")=="PASS",
"paper":r.get("paper_only") is True,
"single":r.get("single_cycle_only") is True,
"loop":r.get("continuous_loop_enabled") is False,
"task":r.get("windows_task_install_enabled") is False,
"broker":r.get("broker_write_enabled") is False,
"submission":r.get("order_submission_enabled") is False,
"network":r.get("network_requests_executed")==0,
"writes":r.get("write_requests_executed")==0,
"orders":r.get("actual_paper_orders_submitted")==0,
"plan":r.get("cycle_plan_written") is True,
"gate":r.get("recovery_gate_written") is True,
"dashboard":r.get("dashboard_state_written") is True,
"state":r.get("state") in {
"WAIT_PILOT_START",
"PILOT_AUTOMATION_RECOVERY_BLOCKED",
"PILOT_AUTOMATION_READY",
"PILOT_AUTOMATION_CYCLE_AUTHORIZED",
"WAIT_AUTOMATION_PREREQUISITES"}}
failed=[k for k,v in checks.items() if not v]
if failed:raise SystemExit("VERIFY=FAIL "+",".join(failed))
print("VERIFY=PASS")
