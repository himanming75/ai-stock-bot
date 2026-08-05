import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"release/dash2_01_to_dash2_04/actual/paper_dashboard_snapshot.json"
if not p.exists():raise SystemExit("VERIFY=FAIL snapshot missing")
r=json.loads(p.read_text(encoding="utf-8"))
c={"account":isinstance(r.get("account"),dict),"orders":isinstance(r.get("orders"),list),"lifecycle":isinstance(r.get("order_lifecycle"),dict),"positions":isinstance(r.get("positions"),list),"risk":isinstance(r.get("risk"),dict),"runtime":isinstance(r.get("runtime"),dict),"read_only":r.get("read_only") is True,"controls":r.get("order_controls_available") is False,"write":r.get("broker_write_enabled") is False,"live":r.get("live_trading_enabled") is False}
f=[k for k,v in c.items() if not v]
if f:raise SystemExit("VERIFY=FAIL "+",".join(f))
print("VERIFY=PASS")
