import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"release/op4_01_to_op4_04/actual/controlled_paper_pilot_foundation_result.json"
if not p.exists():raise SystemExit("VERIFY=FAIL result missing")
r=json.loads(p.read_text(encoding="utf-8"))
checks={
"status":r.get("status")=="PASS",
"paper":r.get("paper_only") is True,
"broker_write":r.get("broker_write_enabled") is False,
"automatic_submission":r.get("automatic_order_submission_enabled") is False,
"live":r.get("live_trading_enabled") is False,
"network":r.get("network_requests_executed")==0,
"writes":r.get("write_requests_executed")==0,
"orders":r.get("actual_paper_orders_submitted")==0,
"dashboard":r.get("dashboard_state_written") is True,
"state":r.get("state") in {
"CONTROLLED_PAPER_PILOT_READY",
"WAIT_OPEN_ORDERS_CLEARANCE",
"WAIT_ORDER_RECOVERY",
"WAIT_PILOT_PREREQUISITES"}}
failed=[k for k,v in checks.items() if not v]
if failed:raise SystemExit("VERIFY=FAIL "+",".join(failed))
print("VERIFY=PASS")
