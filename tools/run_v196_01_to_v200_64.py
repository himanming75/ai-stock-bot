from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from multi_broker_production.engine import evaluate
r=evaluate(ROOT)
s=r["unified_portfolio"]["summary"]
print(json.dumps({
    "stage":r["stage"],"state":r["state"],"status":r["status"],
    "broker_count":s["broker_count"],
    "account_count":s["account_count"],
    "position_count":s["position_count"],
    "healthy_broker_count":r["broker_health"]["healthy_broker_count"],
    "total_equity":s["total_equity"],
    "total_cash":s["total_cash"],
    "read_failover_ready":r["read_failover_ready"],
    "automatic_write_failover_enabled":False,
    "broker_write_enabled":False,
    "actual_live_orders_submitted":0,
    "next_phase":r["next_phase"],
},indent=2,sort_keys=True))
