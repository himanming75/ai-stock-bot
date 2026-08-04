from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from v120_final_release.engine import evaluate
r=evaluate(ROOT)
print(json.dumps({
"stage":r.get("stage"),"state":r.get("state"),"status":r.get("status"),
"release_id":r.get("release_id"),"release_version":r.get("release_version"),
"base_commit":r.get("base_commit"),
"ready_stages":r.get("integration",{}).get("ready_stage_count"),
"total_stages":r.get("integration",{}).get("stage_count"),
"development_complete":r.get("development_complete"),
"production_release_created":r.get("production_release_created"),
"paper_trading_ready":r.get("paper_trading_ready"),
"live_trading_ready":r.get("live_trading_ready"),
"integrity_passed":r.get("integrity",{}).get("passed"),
"acceptance_passed":r.get("acceptance",{}).get("passed"),
"actual_orders_submitted":r.get("actual_orders_submitted"),
"next_phase":r.get("next_phase"),
},indent=2,sort_keys=True))
print("RESULT_FILE="+str((ROOT/"release/v120_final/actual/v120_final_release_result.json").resolve()))
print("FINAL_BUNDLE="+str((ROOT/"release/v120_final/bundle/AI_STOCK_BOT_V120_FINAL.zip").resolve()))
