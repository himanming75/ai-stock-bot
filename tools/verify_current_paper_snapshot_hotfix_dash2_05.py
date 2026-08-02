import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/"release/dash2_05/actual/current_paper_snapshot_collector_result.json"
if not p.exists():raise SystemExit("VERIFY=FAIL collector result missing")
r=json.loads(p.read_text(encoding="utf-8"))
checks={
"status":r.get("status")=="PASS",
"paper":r.get("paper_only") is True,
"read_only":r.get("read_only") is True,
"writes":r.get("write_requests_executed")==0,
"orders":r.get("actual_paper_orders_submitted")==0,
"live":r.get("live_orders_submitted")==0,
"state":r.get("state") in {
"WAIT_CURRENT_PAPER_SNAPSHOT_NETWORK_READ",
"CURRENT_PAPER_SNAPSHOT_READY"}}
failed=[k for k,v in checks.items() if not v]
if failed:raise SystemExit("VERIFY=FAIL "+",".join(failed))
print("VERIFY=PASS")
