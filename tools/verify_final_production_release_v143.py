import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"release/v143_final/actual/final_production_release_result.json"
if not p.exists():raise SystemExit("VERIFY=FAIL result missing")
r=json.loads(p.read_text());c={"status":r.get("status")=="PASS","safe":r.get("safe_mode_engaged") is False,"network":r.get("network_requests_executed")==0,"paper":r.get("actual_paper_orders_submitted")==0,"live":r.get("live_orders_submitted")==0,"auto":r.get("automatic_start_enabled") is False,"state":r.get("state") in {"WAIT_SCHEDULED_RUNTIME","V143_FINAL_PRODUCTION_PACKAGE_READY"}}
f=[k for k,v in c.items() if not v]
if f:raise SystemExit("VERIFY=FAIL "+",".join(f))
print("VERIFY=PASS")
