import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"release/v81_05_to_v81_08/actual/shadow_execution_result.json"
if not p.exists(): raise SystemExit("VERIFY=FAIL result missing")
r=json.loads(p.read_text(encoding="utf-8")); c={"status":r.get("status")=="PASS","shadow":r.get("shadow_only") is True,"read":r.get("read_only") is True,"broker":r.get("broker_write_enabled") is False,"submit":r.get("order_submission_enabled") is False,"network":r.get("network_requests_executed")==0,"writes":r.get("write_requests_executed")==0,"orders":r.get("actual_paper_orders_submitted")==0,"state":r.get("state") in {"WAIT_SHADOW_TRADING_FOUNDATION","SHADOW_EXECUTION_NO_ACTION","SHADOW_EXECUTION_FILLED"}}; f=[k for k,v in c.items() if not v]
if f: raise SystemExit("VERIFY=FAIL "+",".join(f))
print("VERIFY=PASS")
