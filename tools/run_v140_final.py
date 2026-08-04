from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from v140_autonomous_release.engine import evaluate
r=evaluate(ROOT)
print(json.dumps({
"stage":r.get("stage"),
"state":r.get("state"),
"status":r.get("status"),
"development_complete":r.get("development_complete"),
"paper_trading_ready":r.get("paper_trading_ready"),
"autonomous_paper_orchestrator_ready":r.get("autonomous_paper_orchestrator_ready"),
"web_controller_ready_for_development":r.get("web_controller_ready_for_development"),
"live_trading_ready":r.get("live_trading_ready"),
"actual_live_orders_submitted":r.get("actual_live_orders_submitted"),
"next_phase":r.get("next_phase"),
},indent=2,sort_keys=True))
print("RESULT_FILE="+str((ROOT/"release/v140_final/actual/v140_final_release_result.json").resolve()))
