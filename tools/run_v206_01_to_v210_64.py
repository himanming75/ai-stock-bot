from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from risk_engine_v2.engine import evaluate
r=evaluate(ROOT)
print(json.dumps({
 "stage":r["stage"],"state":r["state"],"status":r["status"],
 "trading_allowed":r["trading_allowed"],
 "drawdown_pct":r["risk_gate"]["metrics"]["drawdown_pct"],
 "daily_loss_pct":r["risk_gate"]["metrics"]["daily_loss_pct"],
 "position_quantity":r["risk_gate"]["position_size"]["quantity"],
 "kill_switch_enabled":r["kill_switch"]["enabled"],
 "execution_authorized":False,
 "broker_write_enabled":False,
 "actual_live_orders_submitted":0,
 "next_phase":r["next_phase"]
},indent=2,sort_keys=True))
