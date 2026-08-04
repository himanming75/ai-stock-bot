from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from ai_strategy_ensemble.engine import evaluate
r=evaluate(ROOT)
print(json.dumps({
"stage":r["stage"],
"state":r["state"],
"status":r["status"],
"champion":r["champion"]["strategy_id"] if r["champion"] else None,
"active_strategy_count":len(r["allocations"]),
"ensemble_signal_count":len(r["ensemble_signal"]["signals"]),
"risk_gate_passed":r["risk_gate_passed"],
"strategy_promotion_authorized":False,
"execution_authorized":False,
"actual_live_orders_submitted":0,
"next_phase":r["next_phase"],
},indent=2,sort_keys=True))
