import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"release/op3_13_to_op3_16/actual/limited_autonomous_paper_trading_result.json"
if not p.exists():raise SystemExit("VERIFY=FAIL result missing")
r=json.loads(p.read_text(encoding="utf-8"))
c={"status":r.get("status")=="PASS","safe":r.get("safe_mode_engaged") is False,"paper":r.get("paper_only") is True,"single":r.get("single_cycle_only") is True,"loop":r.get("continuous_loop_enabled") is False,"network":r.get("network_requests_executed")==0,"writes":r.get("write_requests_executed")==0,"orders":r.get("actual_paper_orders_submitted")==0,"live":r.get("live_orders_submitted")==0,"state":r.get("state") in {"LIMITED_AUTONOMOUS_PAPER_CYCLE_ARMED","LIMITED_AUTONOMOUS_PAPER_CYCLE_HOLD"}}
f=[k for k,v in c.items() if not v]
if f:raise SystemExit("VERIFY=FAIL "+",".join(f))
print("VERIFY=PASS")
