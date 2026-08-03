import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"release/v81_01_to_v81_04/actual/shadow_trading_foundation_result.json"
if not p.exists(): raise SystemExit("VERIFY=FAIL result missing")
r=json.loads(p.read_text(encoding="utf-8")); c={"status":r.get("status")=="PASS","paper":r.get("paper_only") is True,"readonly":r.get("read_only") is True,"broker":r.get("broker_write_enabled") is False,"orders":r.get("actual_paper_orders_submitted")==0,"network":r.get("network_requests_executed")==0,"writes":r.get("write_requests_executed")==0,"state":r.get("state") in {"WAIT_PAPER_TRADING_COMPLETION","WAIT_ACCOUNT_SNAPSHOT","SHADOW_TRADING_READY"}}
f=[k for k,v in c.items() if not v]
if f: raise SystemExit("VERIFY=FAIL "+",".join(f))
print("VERIFY=PASS")
