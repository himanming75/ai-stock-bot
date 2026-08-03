from __future__ import annotations
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

def load_json(path:Path)->dict[str,Any]:
    if not path.exists(): return {}
    x=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise ValueError(f"JSON object required: {path}")
    return x

def write_json(path:Path,payload:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def append_jsonl(path:Path,payload:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8",newline="\n") as f: f.write(json.dumps(payload,sort_keys=True)+"\n")

def make_id(prefix:str,payload:dict[str,Any])->str:
    return prefix+"-"+hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:20]

def run_shadow_execution(foundation_result_path:Path,observation_path:Path,policy_path:Path,order_ledger_path:Path,fill_ledger_path:Path,execution_report_path:Path,dashboard_path:Path,result_path:Path)->dict[str,Any]:
    issues=[]
    try: foundation=load_json(foundation_result_path)
    except Exception as e: foundation={}; issues.append({"code":"INVALID_FOUNDATION_RESULT","blocking":True,"detail":str(e)})
    try: obs=load_json(observation_path)
    except Exception as e: obs={}; issues.append({"code":"INVALID_OBSERVATION","blocking":True,"detail":str(e)})
    try: policy=load_json(policy_path)
    except Exception as e: policy={}; issues.append({"code":"INVALID_POLICY","blocking":True,"detail":str(e)})
    if not policy: issues.append({"code":"POLICY_NOT_FOUND","blocking":True,"detail":str(policy_path)})
    if policy and not bool(policy.get("shadow_only",False)): issues.append({"code":"SHADOW_ONLY_REQUIRED","blocking":True})
    if policy and bool(policy.get("broker_write_enabled",True)): issues.append({"code":"BROKER_WRITE_MUST_BE_DISABLED","blocking":True})
    if policy and bool(policy.get("live_trading_enabled",True)): issues.append({"code":"LIVE_TRADING_MUST_BE_DISABLED","blocking":True})
    ready=foundation.get("state")=="SHADOW_TRADING_READY"
    symbol=str(obs.get("symbol","")).upper(); side=str(obs.get("shadow_action","HOLD")).upper(); qty=int(obs.get("quantity",0) or 0); ref=float(obs.get("reference_price",0) or 0)
    maxq=int(policy.get("maximum_quantity",100) or 100); bps=float(policy.get("fixed_slippage_bps",2) or 0); cps=float(policy.get("commission_per_share",0) or 0); minc=float(policy.get("minimum_commission",0) or 0)
    if qty<0 or qty>maxq: issues.append({"code":"QUANTITY_GATE_BLOCKED","blocking":True,"detail":str(qty)})
    if side in {"BUY","SELL"} and (not symbol or ref<=0): issues.append({"code":"INVALID_EXECUTION_INPUT","blocking":True})
    now=datetime.now(timezone.utc).isoformat(); order_created=False; fill_created=False; oid=""; fid=""; fill_price=slip=comm=gross=effective=0.0
    if any(i.get("blocking") for i in issues): state,status="SHADOW_EXECUTION_SAFE_MODE","BLOCKED"
    elif not ready: state,status="WAIT_SHADOW_TRADING_FOUNDATION","PASS"
    elif side=="HOLD" or qty==0: state,status="SHADOW_EXECUTION_NO_ACTION","PASS"
    else:
        delta=ref*bps/10000.0; fill_price=ref+delta if side=="BUY" else ref-delta; slip=delta*qty; comm=max(minc,qty*cps); gross=fill_price*qty; effective=gross+comm if side=="BUY" else gross-comm
        seed={"symbol":symbol,"side":side,"quantity":qty,"reference_price":ref,"observed_at":obs.get("observed_at","")}; oid=make_id("shadow-order",seed)
        order={"stage":"V81.05","order_id":oid,"symbol":symbol,"side":side,"quantity":qty,"order_type":"SHADOW_MARKET","reference_price":ref,"status":"VIRTUAL_FILLED","broker_action_performed":False,"created_at":now}; append_jsonl(order_ledger_path,order); order_created=True
        fid=make_id("shadow-fill",{"order_id":oid,"fill_price":fill_price,"commission":comm})
        fill={"stage":"V81.06","fill_id":fid,"order_id":oid,"symbol":symbol,"side":side,"quantity":qty,"fill_price":round(fill_price,8),"slippage_total":round(slip,8),"commission":round(comm,8),"gross_notional":round(gross,8),"effective_cost":round(effective,8),"broker_action_performed":False,"filled_at":now}; append_jsonl(fill_ledger_path,fill); fill_created=True; state,status="SHADOW_EXECUTION_FILLED","PASS"
    report={"stage_range":"V81.05-V81.08","order_id":oid,"fill_id":fid,"symbol":symbol,"side":side,"quantity":qty,"reference_price":ref,"virtual_fill_price":round(fill_price,8),"slippage_total":round(slip,8),"commission":round(comm,8),"gross_notional":round(gross,8),"effective_cost":round(effective,8),"shadow_order_created":order_created,"virtual_fill_created":fill_created,"broker_action_performed":False,"observed_at":now}; write_json(execution_report_path,report)
    dash={"stage":"V81.08","execution_state":state,**{k:report[k] for k in ["symbol","side","quantity","reference_price","virtual_fill_price","slippage_total","commission","effective_cost","shadow_order_created","virtual_fill_created"]},"read_only":True,"broker_write_enabled":False,"order_submission_enabled":False,"live_trading_enabled":False,"observed_at":now}; write_json(dashboard_path,dash)
    result={"stage_range":"V81.05-V81.08","implementation_type":"SHADOW_EXECUTION_ENGINE","status":status,"state":state,"foundation_ready":ready,**{k:report[k] for k in ["shadow_order_created","virtual_fill_created","order_id","fill_id","symbol","side","quantity","reference_price","virtual_fill_price","slippage_total","commission","effective_cost"]},"execution_report_written":True,"dashboard_state_written":True,"shadow_only":True,"paper_only":True,"read_only":True,"broker_write_enabled":False,"order_submission_enabled":False,"cancel_enabled":False,"replace_enabled":False,"position_close_enabled":False,"live_trading_enabled":False,"actual_credentials_used":False,"actual_external_network_used":False,"network_requests_executed":0,"write_requests_executed":0,"actual_paper_orders_submitted":0,"live_orders_submitted":0,"issue_count":len(issues),"blocking_issue_count":sum(1 for i in issues if i.get("blocking")),"issues":issues,"next_phase":"V81_09_SHADOW_PORTFOLIO_PNL" if state in {"SHADOW_EXECUTION_FILLED","SHADOW_EXECUTION_NO_ACTION"} else "V81_05_TO_V81_08_WAIT_EXECUTION_GATE","validation_mode":"LOCAL_SHADOW_EXECUTION_ONLY","observed_at":now,"result_path":str(result_path.resolve())}; write_json(result_path,result); return result
