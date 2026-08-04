from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from paper_qualification.engine import evaluate
r=evaluate(ROOT)
print(json.dumps({
"stage":r["stage"],"state":r["state"],"status":r["status"],
"trading_days":r["metrics"]["trading_days"],
"closed_trades":r["metrics"]["closed_trades"],
"win_rate_pct":r["metrics"]["win_rate_pct"],
"profit_factor":r["metrics"]["profit_factor"],
"sharpe":r["metrics"]["sharpe"],
"maximum_drawdown_pct":r["metrics"]["maximum_drawdown_pct"],
"qualification_passed":r["qualification"]["passed"],
"actual_live_orders_submitted":0,
"next_phase":r["next_phase"],
},indent=2,sort_keys=True))
