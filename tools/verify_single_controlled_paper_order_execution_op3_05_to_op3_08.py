import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"release/op3_05_to_op3_08/actual/single_controlled_paper_order_execution_result.json"
if not p.exists():raise SystemExit("VERIFY=FAIL result missing")
r=json.loads(p.read_text(encoding="utf-8"))
checks={
"status":r.get("status")=="PASS",
"safe":r.get("safe_mode_engaged") is False,
"paper_only":r.get("paper_only") is True,
"live":r.get("live_orders_submitted")==0,
"default_network":r.get("network_requests_executed")==0,
"default_write":r.get("write_requests_executed")==0,
"default_paper_orders":r.get("actual_paper_orders_submitted")==0,
"state":r.get("state") in {
"SINGLE_PAPER_ORDER_EXECUTION_ARMED",
"WAIT_CONTROLLED_PAPER_PREPARATION"}}
failed=[k for k,v in checks.items() if not v]
if failed:raise SystemExit("VERIFY=FAIL "+",".join(failed))
print("VERIFY=PASS")
