from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from multi_account_engine.io import load_json,write_json
DEFAULT={"accounts":[
{"account_id":"PAPER_SCALP","broker":"ALPACA","environment":"PAPER","enabled":True,"credential_prefix":"ALPACA_PAPER_SCALP","assigned_profiles":["SCALP"],"capital_limit":25000.0,"daily_loss_limit_pct":1.0,"maximum_drawdown_pct":5.0,"maximum_positions":3,"maximum_orders_per_day":10,"kill_switch_enabled":True},
{"account_id":"PAPER_DAY","broker":"ALPACA","environment":"PAPER","enabled":True,"credential_prefix":"ALPACA_PAPER_DAY","assigned_profiles":["DAY"],"capital_limit":45000.0,"daily_loss_limit_pct":1.5,"maximum_drawdown_pct":7.0,"maximum_positions":5,"maximum_orders_per_day":15,"kill_switch_enabled":True},
{"account_id":"PAPER_SWING","broker":"ALPACA","environment":"PAPER","enabled":True,"credential_prefix":"ALPACA_PAPER_SWING","assigned_profiles":["SWING"],"capital_limit":30000.0,"daily_loss_limit_pct":2.0,"maximum_drawdown_pct":10.0,"maximum_positions":5,"maximum_orders_per_day":5,"kill_switch_enabled":True}],
"allow_cross_account_symbol_overlap":False,"paper_read_enabled":False,"paper_submission_enabled":False,"live_submission_enabled":False,"live_network_enabled":False,"broker_write_enabled":False}
def path(root): return Path(root)/"release/v281_01_to_v290_64/config/multi_account_policy.json"
def load(root):
 v=load_json(path(root))
 if not v:
  v=deepcopy(DEFAULT); v["updated_at"]=datetime.now(timezone.utc).isoformat(); write_json(path(root),v)
 return v
def validate(v):
 e=[]; a=v.get("accounts",[]); ids=[x.get("account_id") for x in a]; prefixes=[x.get("credential_prefix") for x in a]
 if len(ids)!=len(set(ids)): e.append("account_id values must be unique")
 if len(prefixes)!=len(set(prefixes)): e.append("credential_prefix values must be unique")
 for x in a:
  if x.get("environment")!="PAPER": e.append(f"{x.get('account_id')} must remain PAPER")
  if x.get("broker")!="ALPACA": e.append(f"{x.get('account_id')} broker must be ALPACA")
 for k in ("paper_read_enabled","paper_submission_enabled","live_submission_enabled","live_network_enabled","broker_write_enabled"):
  if v.get(k) is not False: e.append(f"{k} must remain false by default")
 return {"valid":not e,"errors":e}
