from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from portfolio_broker.engine import evaluate
r=evaluate(ROOT)
s=r["portfolio"]["summary"]
print(json.dumps({
    "stage":r["stage"],"state":r["state"],"status":r["status"],
    "broker_count":len(r["registered_brokers"]),
    "account_count":s["account_count"],
    "position_count":s["position_count"],
    "total_equity":s["total_equity"],
    "total_cash":s["total_cash"],
    "gross_exposure_pct":s["gross_exposure_pct"],
    "risk_gate_passed":r["portfolio_risk_gate"]["passed"],
    "broker_write_enabled":r["broker_write_enabled"],
    "actual_live_orders_submitted":0,
    "next_phase":r["next_phase"],
},indent=2,sort_keys=True))
