import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"release/dash1_05_to_dash1_08/actual/dashboard_advanced_snapshot.json"
if not p.exists():raise SystemExit("VERIFY=FAIL snapshot missing")
r=json.loads(p.read_text(encoding="utf-8"))
c={"performance":isinstance(r.get("performance"),dict),"events":isinstance(r.get("events"),list),"alerts":isinstance(r.get("alerts"),list),"health":isinstance(r.get("health"),dict),"read_only":r.get("read_only") is True,"submission":r.get("order_submission_enabled") is False,"broker_write":r.get("broker_write_enabled") is False,"live":r.get("live_trading_enabled") is False}
f=[k for k,v in c.items() if not v]
if f:raise SystemExit("VERIFY=FAIL "+",".join(f))
print("VERIFY=PASS")
