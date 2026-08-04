from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from multi_account_engine.engine import evaluate
r=evaluate(ROOT)
print(json.dumps({"stage":r["stage"],"state":r["state"],"status":r["status"],"account_count":len(r["accounts"]),"route_count":len(r["routes"]),"accounts":[{"account_id":x["account_id"],"assigned_profiles":x["assigned_profiles"],"credential_ready":x["credential_state"]["ready"],"risk_passed":x["risk_state"]["passed"],"route_count":len(x["routes"]),"kill_switch_clear":x["risk_state"]["checks"]["kill_switch_clear"]} for x in r["accounts"]],"paper_read_enabled":False,"paper_submission_enabled":False,"live_submission_enabled":False,"actual_live_orders_submitted":0,"next_phase":r["next_phase"]},indent=2,sort_keys=True))
