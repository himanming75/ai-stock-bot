import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"release/op1_17_to_op1_20/actual/windows_scheduled_collection_result.json"
if not p.exists():raise SystemExit("VERIFY=FAIL result missing")
r=json.loads(p.read_text());c={"status":r.get("status")=="PASS","safe":r.get("safe_mode_engaged") is False,"network":r.get("network_requests_executed")==0,"write":r.get("write_requests_executed")==0,"paper":r.get("actual_paper_orders_submitted")==0,"live":r.get("live_orders_submitted")==0,"task_not_installed":r.get("task_installed") is False,"auto_disabled":r.get("automatic_start_enabled") is False,"state":r.get("state") in {"WAIT_AUTOMATIC_SNAPSHOT_COLLECTOR","WINDOWS_SCHEDULED_READ_ONLY_PLAN_READY"}}
f=[k for k,v in c.items() if not v]
if f:raise SystemExit("VERIFY=FAIL "+",".join(f))
print("VERIFY=PASS")
