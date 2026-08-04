import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from paper_web_ops.settings import load,validate
from paper_web_ops.state import build
s=load(ROOT);v=validate(s);d=build(ROOT)
checks={"settings_valid":v["valid"],"paper_read_enabled":s["real_paper_read_enabled"] is True,"paper_shadow_enabled":s["real_paper_shadow_enabled"] is True,"paper_submission_default_off":s["paper_submission_enabled"] is False,"one_order_limit":s["maximum_orders_per_web_cycle"]==1,"paper_only":s["paper_only"] is True,"live_disabled":s["live_submission_enabled"] is False,"live_orders_zero":d["safety"]["actual_live_orders_submitted"]==0,"paper_api_present":(ROOT/"web_controller/paper_api.py").exists()}
failed=[k for k,x in checks.items() if not x]
r={"verification_stage":"V155.64","verification_status":"PASS" if not failed else "FAIL","controller_url":"http://127.0.0.1:8765","settings":s,"credential_detection":d["credentials"],"safety":d["safety"],"checks":checks,"failed":failed}
print(json.dumps(r,indent=2,sort_keys=True));out=ROOT/"release/v151_01_to_v155_64/actual/paper_web_operations_verification.json";out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8");raise SystemExit(0 if not failed else 1)
