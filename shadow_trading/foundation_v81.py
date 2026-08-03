from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def load_json(path: Path) -> dict[str, Any]:
    if not path.exists(): return {}
    data=json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data,dict) else {}

def write_json(path: Path,payload: dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def run_shadow_foundation(completion_result_path:Path,snapshot_path:Path,signal_path:Path,policy_path:Path,result_path:Path,dashboard_path:Path,observation_path:Path)->dict[str,Any]:
    completion=load_json(completion_result_path); snapshot=load_json(snapshot_path); signal=load_json(signal_path); policy=load_json(policy_path)
    issues=[]
    if not policy: issues.append({"code":"POLICY_NOT_FOUND","blocking":True})
    if policy and not bool(policy.get("paper_only",False)): issues.append({"code":"PAPER_ONLY_REQUIRED","blocking":True})
    if policy and bool(policy.get("broker_write_enabled",True)): issues.append({"code":"BROKER_WRITE_MUST_BE_DISABLED","blocking":True})
    if policy and bool(policy.get("live_trading_enabled",True)): issues.append({"code":"LIVE_TRADING_MUST_BE_DISABLED","blocking":True})
    completion_ready=bool(completion.get("completion_ready",False))
    if any(x.get("blocking") for x in issues): state,status="SHADOW_TRADING_SAFE_MODE","BLOCKED"
    elif not completion_ready: state,status="WAIT_PAPER_TRADING_COMPLETION","PASS"
    elif not snapshot: state,status="WAIT_ACCOUNT_SNAPSHOT","PASS"
    else: state,status="SHADOW_TRADING_READY","PASS"
    account=snapshot.get("account",{}) if isinstance(snapshot.get("account"),dict) else {}
    positions=snapshot.get("positions",[]); open_orders=snapshot.get("open_orders",[])
    action=str(signal.get("approved_action",signal.get("action","HOLD"))).upper(); action=action if action in {"BUY","SELL"} else "HOLD"
    symbol=str(signal.get("symbol","")).upper(); qty=int(signal.get("quantity",0) or 0); price=float(signal.get("reference_price",0) or 0)
    now=datetime.now(timezone.utc).isoformat()
    obs={"stage":"V81.03","symbol":symbol,"shadow_action":action,"quantity":qty,"reference_price":price,"virtual_fill_price":price,"virtual_notional":round(price*qty,8),"account_status":account.get("status",""),"portfolio_value":float(account.get("portfolio_value",0) or 0),"position_count":len(positions) if isinstance(positions,list) else 0,"open_order_count":len(open_orders) if isinstance(open_orders,list) else 0,"broker_action_performed":False,"observed_at":now}
    write_json(observation_path,obs)
    write_json(dashboard_path,{"stage":"V81.04","shadow_state":state,"completion_ready":completion_ready,"symbol":symbol,"shadow_action":action,"virtual_fill_price":price,"virtual_notional":round(price*qty,8),"read_only":True,"broker_write_enabled":False,"live_trading_enabled":False,"observed_at":now})
    result={"stage_range":"V81.01-V81.04","implementation_type":"READ_ONLY_SHADOW_TRADING_FOUNDATION","status":status,"state":state,"completion_ready":completion_ready,"snapshot_ready":bool(snapshot),"signal_ready":bool(signal),"shadow_observation_written":True,"dashboard_state_written":True,"paper_only":True,"read_only":True,"broker_write_enabled":False,"order_submission_enabled":False,"cancel_enabled":False,"replace_enabled":False,"position_close_enabled":False,"live_trading_enabled":False,"actual_credentials_used":False,"actual_external_network_used":False,"network_requests_executed":0,"write_requests_executed":0,"actual_paper_orders_submitted":0,"live_orders_submitted":0,"issue_count":len(issues),"blocking_issue_count":sum(1 for x in issues if x.get("blocking")),"issues":issues,"next_phase":"V81_05_SHADOW_SLIPPAGE_ANALYTICS" if state=="SHADOW_TRADING_READY" else "V81_WAIT_FOUNDATION_GATE","observed_at":now,"result_path":str(result_path.resolve())}
    write_json(result_path,result); return result
