import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"release/op3_01_to_op3_04/actual/controlled_paper_order_preparation_result.json"
if not p.exists():raise SystemExit("VERIFY=FAIL result missing")
r=json.loads(p.read_text(encoding="utf-8"))
checks={
"status":r.get("status")=="PASS",
"safe":r.get("safe_mode_engaged") is False,
"paper_only":r.get("paper_only") is True,
"preparation_only":r.get("preparation_only") is True,
"submission":r.get("order_submission_enabled") is False,
"network_write":r.get("network_write_enabled") is False,
"network_requests":r.get("network_requests_executed")==0,
"write_requests":r.get("write_requests_executed")==0,
"paper_orders":r.get("actual_paper_orders_submitted")==0,
"live_orders":r.get("live_orders_submitted")==0,
"state":r.get("state") in {
"WAIT_CONTROLLED_PAPER_INPUT",
"CONTROLLED_PAPER_ORDER_PREPARATION_READY"}}
failed=[k for k,v in checks.items() if not v]
if failed:raise SystemExit("VERIFY=FAIL "+",".join(failed))
print("VERIFY=PASS")
