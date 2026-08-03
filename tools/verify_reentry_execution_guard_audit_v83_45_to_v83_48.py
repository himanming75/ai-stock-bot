import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/"release/v83_45_to_v83_48/actual/reentry_execution_guard_audit_result.json"
if not p.exists(): raise SystemExit("RESULT NOT FOUND: "+str(p))
r=json.loads(p.read_text())
safe={"REENTRY_EXECUTION_GUARD_WAIT_APPROVAL","REENTRY_EXECUTION_DRY_RUN_READY","REENTRY_EXECUTION_SUPERVISED_READY","REENTRY_EXECUTION_GUARD_ACTIVE","REENTRY_EXECUTION_LOCK_CLEARED"}
c={"stage_range":r.get("stage_range")=="V83.45-V83.48","status":r.get("status")=="PASS","state":r.get("state") in safe,"paper_only":r.get("paper_only") is True,"automatic_execution_disabled":r.get("automatic_execution_enabled") is False,"broker_write_disabled":r.get("broker_write_enabled") is False,"order_submission_disabled":r.get("order_submission_enabled") is False,"live_trading_disabled":r.get("live_trading_enabled") is False,"external_network_unused":r.get("actual_external_network_used") is False,"network_requests_zero":r.get("network_requests_executed")==0,"write_requests_zero":r.get("write_requests_executed")==0,"paper_orders_zero":r.get("actual_paper_orders_submitted")==0,"live_orders_zero":r.get("live_orders_submitted")==0}
f=[k for k,v in c.items() if not v]
print(json.dumps({"verification_stage":"V83.48","verification_status":"PASS" if not f else "FAIL","source_state":r.get("state"),"checks":c,"failed":f},indent=2,sort_keys=True))
raise SystemExit(1 if f else 0)
