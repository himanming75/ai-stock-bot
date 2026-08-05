from __future__ import annotations
import json,os,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from multi_broker_etrade_oauth.sandbox_read import build_sandbox_adapter
def required(name):
    value=os.environ.get(name,"").strip()
    if not value: raise RuntimeError(f"Missing environment variable: {name}")
    return value
adapter=build_sandbox_adapter(consumer_key=required("ETRADE_CONSUMER_KEY"),consumer_secret=required("ETRADE_CONSUMER_SECRET"),access_token=required("ETRADE_ACCESS_TOKEN"),access_secret=required("ETRADE_ACCESS_SECRET"),account_id_key=os.environ.get("ETRADE_ACCOUNT_ID_KEY","").strip() or None)
account=adapter.get_account(); positions=adapter.list_positions(); orders=adapter.list_orders()
result={"stage":"ETRADE_ACTUAL_SANDBOX_ACCOUNT_READ_CERTIFICATION","status":"PASS","generated_at":datetime.now(timezone.utc).isoformat(),"account":account.to_dict(),"positions":[x.to_dict() for x in positions],"orders":[x.to_dict() for x in orders],"actual_external_network_used":True,"actual_broker_read_performed":True,"actual_broker_write_performed":False,"actual_order_submission_performed":False,"actual_paper_orders_submitted":0,"actual_live_orders_submitted":0}
path=Path("release/v3801_4000_etrade_sandbox_certification/actual/actual_sandbox_read_certification.json"); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(result,indent=2,sort_keys=True))
