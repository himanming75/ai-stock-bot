import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"release/op3_09_to_op3_12/actual/paper_order_lifecycle_result.json"
if not p.exists():raise SystemExit("VERIFY=FAIL result missing")
r=json.loads(p.read_text(encoding="utf-8"))
checks={
"status":r.get("status")=="PASS",
"safe":r.get("safe_mode_engaged") is False,
"paper_only":r.get("paper_only") is True,
"read_only":r.get("read_only") is True,
"writes":r.get("write_requests_executed")==0,
"new_orders":r.get("actual_paper_orders_submitted")==0,
"live_orders":r.get("live_orders_submitted")==0,
"cancel":r.get("cancel_enabled") is False,
"replace":r.get("replace_enabled") is False,
"state":r.get("state") in {
"PAPER_ORDER_LIFECYCLE_COMPLETE",
"PAPER_ORDER_LIFECYCLE_MONITORING"}}
failed=[k for k,v in checks.items() if not v]
if failed:raise SystemExit("VERIFY=FAIL "+",".join(failed))
print("VERIFY=PASS")
