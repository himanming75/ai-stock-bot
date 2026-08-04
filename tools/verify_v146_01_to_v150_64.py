import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from strategy_manager.config import load,validate
from strategy_manager.apply import build_runtime_policy
c=load(ROOT);v=validate(c);p=build_runtime_policy(ROOT)
checks={"config_valid":v["valid"],"strategy_enabled":len(p["enabled_strategies"])>=1,"symbols_present":len(p["symbols"])>=1,"paper_only":p["paper_only"] is True,"live_disabled":p["live_submission_enabled"] is False,"live_orders_zero":p["actual_live_orders_submitted"]==0,"web_strategy_api":(ROOT/"web_controller/strategy_api.py").exists()}
failed=[k for k,x in checks.items() if not x]
r={"verification_stage":"V150.64","verification_status":"PASS" if not failed else "FAIL","enabled_strategies":p["enabled_strategies"],"symbols":p["symbols"],"risk":{"maximum_order_notional":p["maximum_order_notional"],"maximum_quantity":p["maximum_quantity"],"maximum_daily_orders":p["maximum_daily_orders"],"maximum_daily_loss":p["maximum_daily_loss"],"maximum_positions":p["maximum_positions"]},"actual_live_orders_submitted":0,"checks":checks,"failed":failed}
print(json.dumps(r,indent=2,sort_keys=True))
out=ROOT/"release/v146_01_to_v150_64/actual/strategy_manager_verification.json";out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8")
raise SystemExit(0 if not failed else 1)
