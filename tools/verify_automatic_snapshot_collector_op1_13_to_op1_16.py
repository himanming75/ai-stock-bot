import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"release/op1_13_to_op1_16/actual/automatic_snapshot_collector_result.json"
if not p.exists():raise SystemExit("VERIFY=FAIL result missing")
r=json.loads(p.read_text());c={"status":r.get("status")=="PASS","safe":r.get("safe_mode_engaged") is False,"write":r.get("write_requests_executed")==0,"paper":r.get("actual_paper_orders_submitted")==0,"live":r.get("live_orders_submitted")==0,"submission":r.get("order_submission_enabled") is False,"live_disabled":r.get("live_trading_enabled") is False,"state":r.get("state") in {"WAIT_WEEKLY_PILOT_REVIEW","AUTOMATIC_SNAPSHOT_COLLECTION_READY"}}
f=[k for k,v in c.items() if not v]
if f:raise SystemExit("VERIFY=FAIL "+",".join(f))
print("VERIFY=PASS")
