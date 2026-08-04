from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from multi_account_engine.engine import evaluate
r=evaluate(ROOT)
c={"stage":r["stage"]=="V290.64","status":r["status"]=="PASS","allowed_state":r["state"] in {"MULTI_ACCOUNT_ENGINE_READY","MULTI_ACCOUNT_ENGINE_REVIEW_REQUIRED"},"accounts_present":bool(r["accounts"]),"routes_present":bool(r["routes"]),"all_accounts_paper":all(a["environment"]=="PAPER" for a in r["accounts"]),"paper_read_disabled":r["paper_read_enabled"] is False,"paper_submission_disabled":r["paper_submission_enabled"] is False,"live_submission_disabled":r["live_submission_enabled"] is False,"live_network_disabled":r["live_network_enabled"] is False,"broker_write_disabled":r["broker_write_enabled"] is False,"paper_orders_zero":r["actual_paper_orders_submitted"]==0,"live_orders_zero":r["actual_live_orders_submitted"]==0,"web_api_present":(ROOT/"web_controller/multi_account_engine_api.py").exists()}
f=[k for k,v in c.items() if not v]; v={"verification_stage":"V290.64","verification_status":"PASS" if not f else "FAIL","state":r["state"],"checks":c,"failed":f,"accounts":r["accounts"],"routes":r["routes"],"actual_paper_orders_submitted":0,"actual_live_orders_submitted":0}
print(json.dumps(v,indent=2,sort_keys=True)); o=ROOT/"release/v281_01_to_v290_64/actual/multi_account_engine_verification.json"; o.parent.mkdir(parents=True,exist_ok=True); o.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n",encoding="utf-8"); raise SystemExit(0 if not f else 1)
