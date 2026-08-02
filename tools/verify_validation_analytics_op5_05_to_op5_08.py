import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"release/op5_05_to_op5_08/actual/validation_analytics_result.json"
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
"analytics":r.get("analytics_written") is True,
"trend":r.get("trend_written") is True,
"report":r.get("report_written") is True,
"dashboard":r.get("dashboard_state_written") is True,
"state":r.get("state") in {
"WAIT_VALIDATION_DATA",
"VALIDATION_ANALYTICS_IN_PROGRESS",
"VALIDATION_ANALYTICS_COMPLETE"}}
failed=[key for key,value in checks.items() if not value]
if failed:raise SystemExit("VERIFY=FAIL "+",".join(failed))
print("VERIFY=PASS")
