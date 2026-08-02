import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"release/op4_05_to_op4_08/actual/paper_session_monitor_result.json"
if not p.exists():raise SystemExit("VERIFY=FAIL result missing")
r=json.loads(p.read_text(encoding="utf-8"))
checks={
"status":r.get("status")=="PASS",
"paper":r.get("paper_only") is True,
"read_only":r.get("read_only") is True,
"broker":r.get("broker_write_enabled") is False,
"submission":r.get("order_submission_enabled") is False,
"network":r.get("network_requests_executed")==0,
"writes":r.get("write_requests_executed")==0,
"orders":r.get("actual_paper_orders_submitted")==0,
"dashboard":r.get("dashboard_state_written") is True,
"state":r.get("state") in {
"WAIT_PILOT_START",
"PAPER_SESSION_HEALTHY",
"PAPER_SESSION_MONITORING",
"PAPER_SESSION_CONTROLLED_STOP_REQUIRED"}}
failed=[k for k,v in checks.items() if not v]
if failed:raise SystemExit("VERIFY=FAIL "+",".join(failed))
print("VERIFY=PASS")
