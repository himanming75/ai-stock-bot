import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/"release/v83_41_to_v83_44/actual/retry_approval_supervised_reentry_result.json"
if not p.exists(): raise SystemExit("RESULT NOT FOUND: "+str(p))
r=json.loads(p.read_text())
safe={"RETRY_APPROVAL_WAIT_PLAN","SUPERVISED_REENTRY_READY","SUPERVISED_REENTRY_COMPLETED","NO_ACTIVE_RETRY_APPROVAL","RETRY_APPROVAL_EXPIRED","RETRY_APPROVAL_LOCK_CLEARED"}
c={"stage_range":r.get("stage_range")=="V83.41-V83.44","status":r.get("status")=="PASS","state":r.get("state") in safe,"paper_only":r.get("paper_only") is True,"automatic_reentry_disabled":r.get("automatic_reentry_execution_enabled") is False,"broker_write_disabled":r.get("broker_write_enabled") is False,"order_submission_disabled":r.get("order_submission_enabled") is False,"live_trading_disabled":r.get("live_trading_enabled") is False,"external_network_unused":r.get("actual_external_network_used") is False,"paper_orders_zero":r.get("actual_paper_orders_submitted")==0,"live_orders_zero":r.get("live_orders_submitted")==0}
f=[k for k,v in c.items() if not v]
print(json.dumps({"verification_stage":"V83.44","verification_status":"PASS" if not f else "FAIL","source_state":r.get("state"),"checks":c,"failed":f},indent=2,sort_keys=True))
raise SystemExit(1 if f else 0)
