import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"release/dash1_01_to_dash1_04/actual/dashboard_snapshot.json"
if not p.exists(): raise SystemExit("VERIFY=FAIL snapshot missing")
r=json.loads(p.read_text(encoding="utf-8"))
checks={
"read_only":r.get("read_only") is True,
"submission":r.get("order_submission_enabled") is False,
"broker_write":r.get("broker_write_enabled") is False,
"live":r.get("live_trading_enabled") is False,
"runtime":isinstance(r.get("runtime"),dict),
"portfolio":isinstance(r.get("portfolio"),dict),
"signal":isinstance(r.get("signal"),dict),
"daily_report":isinstance(r.get("daily_report"),dict)}
failed=[k for k,v in checks.items() if not v]
if failed: raise SystemExit("VERIFY=FAIL "+",".join(failed))
print("VERIFY=PASS")
