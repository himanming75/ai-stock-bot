from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def load_json(path: Path) -> dict[str, Any]:
    if not path.exists(): return {}
    value=json.loads(path.read_text(encoding='utf-8'))
    return value if isinstance(value,dict) else {}

def write_json(path: Path,payload: dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')

def append_jsonl(path: Path,payload: dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8',newline='\n') as f: f.write(json.dumps(payload,sort_keys=True)+'\n')

def decide_next_action(*,session,scheduler,intraday,end_of_day,multi_day):
    ss=str(session.get('state','')); sc=str(scheduler.get('state','')); ins=str(intraday.get('state','')); es=str(end_of_day.get('state','')); ms=str(multi_day.get('state',''))
    mo=bool(session.get('market_open',False)); mc=bool(session.get('market_closed',False)); active=bool(session.get('session_active',False))
    if ins=='INTRADAY_LOOP_RECOVERY_REQUIRED': return {'action':'RESUME_INTRADAY_LOOP','action_ready':True,'reasons':['INTRADAY_RECOVERY_REQUIRED']}
    if sc=='PAPER_SCHEDULER_HEARTBEAT_TIMEOUT': return {'action':'REFRESH_SCHEDULER_HEARTBEAT','action_ready':True,'reasons':['SCHEDULER_HEARTBEAT_TIMEOUT']}
    if mo and not active: return {'action':'START_PAPER_SESSION','action_ready':ss in {'PAPER_SESSION_READY_TO_START','PAPER_SESSION_CLOSED','PAPER_SESSION_NOT_ACTIVE'},'reasons':['MARKET_OPEN_SESSION_INACTIVE']}
    if active and mo:
        if sc=='PAPER_SCHEDULER_TICK_AUTHORIZED': return {'action':'EXECUTE_INTRADAY_LOOP','action_ready':ins=='INTRADAY_LOOP_READY','reasons':['AUTHORIZED_TICK_AVAILABLE']}
        if ins=='INTRADAY_LOOP_COMPLETE': return {'action':'COMPLETE_SCHEDULER_TICK','action_ready':True,'reasons':['INTRADAY_LOOP_COMPLETE']}
        if sc=='PAPER_SCHEDULER_TICK_DUE': return {'action':'AUTHORIZE_SCHEDULER_TICK','action_ready':True,'reasons':['SCHEDULER_TICK_DUE']}
        return {'action':'REFRESH_SCHEDULER_HEARTBEAT','action_ready':True,'reasons':['SESSION_RUNNING_WAIT_NEXT_TICK']}
    if mc and active: return {'action':'END_PAPER_SESSION','action_ready':True,'reasons':['MARKET_CLOSED_SESSION_ACTIVE']}
    if mc and not active:
        if es=='END_OF_DAY_READY_TO_CERTIFY': return {'action':'CERTIFY_TRADING_DAY','action_ready':True,'reasons':['END_OF_DAY_GATES_CLEAR']}
        if es=='DAILY_PAPER_CERTIFIED': return {'action':'PREPARE_NEXT_TRADING_DAY','action_ready':True,'reasons':['DAILY_CERTIFICATION_COMPLETE']}
        if es=='NEXT_TRADING_DAY_READY' or ms=='MULTI_DAY_ROLLOVER_READY': return {'action':'EXECUTE_MULTI_DAY_ROLLOVER','action_ready':ms=='MULTI_DAY_ROLLOVER_READY','reasons':['NEXT_TRADING_DAY_PREPARED']}
        if ms=='MULTI_DAY_ROLLOVER_COMPLETE': return {'action':'WAIT_NEXT_MARKET_OPEN','action_ready':True,'reasons':['ROLLOVER_COMPLETE']}
        return {'action':'REFRESH_END_OF_DAY_STATE','action_ready':True,'reasons':['END_OF_DAY_GATES_NOT_READY']}
    return {'action':'WAIT','action_ready':True,'reasons':['NO_AUTOMATED_TRANSITION_READY']}

def run_automated_paper_orchestrator(*,session_result_path,scheduler_result_path,intraday_result_path,end_of_day_result_path,multi_day_result_path,policy_path,action_lock_path,action_plan_path,action_ledger_path,recovery_path,dashboard_path,result_path,authorize_action=False,complete_action=False,clear_action_lock=False):
    now=datetime.now(timezone.utc).isoformat(); issues=[]
    vals={}
    for name,path in {'session':session_result_path,'scheduler':scheduler_result_path,'intraday':intraday_result_path,'end_of_day':end_of_day_result_path,'multi_day':multi_day_result_path,'policy':policy_path}.items():
        try: vals[name]=load_json(path)
        except Exception as e: vals[name]={}; issues.append({'code':f'INVALID_{name.upper()}_INPUT','blocking':True,'detail':str(e)})
    policy=vals['policy']
    if not policy: issues.append({'code':'ORCHESTRATOR_POLICY_NOT_FOUND','blocking':True,'detail':str(policy_path)})
    checks=[('PAPER_ONLY_REQUIRED',bool(policy.get('paper_only',False))),('BROKER_WRITE_MUST_BE_DISABLED',not bool(policy.get('broker_write_enabled',True))),('ORDER_SUBMISSION_MUST_BE_DISABLED',not bool(policy.get('order_submission_enabled',True))),('LIVE_TRADING_MUST_BE_DISABLED',not bool(policy.get('live_trading_enabled',True))),('CONTINUOUS_LOOP_MUST_BE_DISABLED',not bool(policy.get('continuous_loop_enabled',True))),('ACTION_EXECUTION_MUST_BE_DISABLED',not bool(policy.get('automatic_action_execution_enabled',True)))]
    for code,ok in checks:
        if not ok: issues.append({'code':code,'blocking':True,'detail':'orchestrator safety policy failed'})
    decision=decide_next_action(session=vals['session'],scheduler=vals['scheduler'],intraday=vals['intraday'],end_of_day=vals['end_of_day'],multi_day=vals['multi_day'])
    lock=load_json(action_lock_path); active=bool(lock.get('active',False)); duplicate=authorize_action and active
    if duplicate: issues.append({'code':'DUPLICATE_ORCHESTRATOR_ACTION_BLOCKED','blocking':True,'detail':str(lock.get('action_id',''))})
    blocking=any(i.get('blocking') for i in issues)
    action_authorized=action_completed=plan_written=lock_written=ledger_written=False
    aid=str(lock.get('action_id',''))
    if blocking: state,status='AUTOMATED_ORCHESTRATOR_SAFE_MODE','BLOCKED'
    elif clear_action_lock:
        write_json(action_lock_path,{'active':False,'action_id':'','cleared_at':now,'paper_only':True}); lock_written=True; state,status='ORCHESTRATOR_ACTION_LOCK_CLEARED','PASS'
    elif complete_action:
        if active:
            append_jsonl(action_ledger_path,{'event':'ORCHESTRATOR_ACTION_COMPLETED','action_id':aid,'action':lock.get('action',''),'completed_at':now,'paper_only':True}); write_json(action_lock_path,{'active':False,'action_id':aid,'action':lock.get('action',''),'completed_at':now,'paper_only':True}); action_completed=lock_written=ledger_written=True; state,status='ORCHESTRATOR_ACTION_COMPLETED','PASS'
        else: state,status='ORCHESTRATOR_NO_ACTIVE_ACTION','PASS'
    elif authorize_action:
        if not decision['action_ready']: state,status='ORCHESTRATOR_ACTION_WAIT_GATES','PASS'
        elif decision['action'] in {'WAIT','WAIT_NEXT_MARKET_OPEN'}: state,status='AUTOMATED_ORCHESTRATOR_WAIT','PASS'
        else:
            aid='orchestrator-action-'+hashlib.sha256(f"{decision['action']}|{now}".encode()).hexdigest()[:20]
            plan={'stage':'V83.02','action_id':aid,'action':decision['action'],'action_ready':True,'reasons':decision['reasons'],'command_execution_enabled':False,'automatic_action_execution_enabled':False,'paper_only':True,'authorized_at':now}
            write_json(action_plan_path,plan); write_json(action_lock_path,{'active':True,'action_id':aid,'action':decision['action'],'authorized_at':now,'paper_only':True}); append_jsonl(action_ledger_path,{**plan,'event':'ORCHESTRATOR_ACTION_AUTHORIZED'}); action_authorized=plan_written=lock_written=ledger_written=True; state,status='ORCHESTRATOR_ACTION_AUTHORIZED','PASS'
    else:
        if active: state,status='ORCHESTRATOR_ACTION_IN_PROGRESS','PASS'
        elif decision['action'] in {'WAIT','WAIT_NEXT_MARKET_OPEN'}: state,status='AUTOMATED_ORCHESTRATOR_WAIT','PASS'
        elif decision['action_ready']: state,status='ORCHESTRATOR_ACTION_READY','PASS'
        else: state,status='ORCHESTRATOR_ACTION_WAIT_GATES','PASS'
    write_json(recovery_path,{'recovery_required':state=='AUTOMATED_ORCHESTRATOR_SAFE_MODE' or active,'active_action':active,'action_id':aid,'action':lock.get('action',decision['action']),'observed_at':now,'paper_only':True})
    write_json(dashboard_path,{'orchestrator_state':state,'recommended_action':decision['action'],'action_ready':decision['action_ready'],'action_reasons':decision['reasons'],'action_id':aid,'active_action':active or action_authorized,'action_authorized':action_authorized,'action_completed':action_completed,'automatic_action_execution_enabled':False,'continuous_loop_enabled':False,'paper_only':True,'read_only':True,'broker_write_enabled':False,'order_submission_enabled':False,'live_trading_enabled':False,'observed_at':now})
    result={'stage_range':'V83.01-V83.04','implementation_type':'AUTOMATED_PAPER_RUNTIME_ORCHESTRATOR_FOUNDATION','status':status,'state':state,'recommended_action':decision['action'],'action_ready':decision['action_ready'],'action_reasons':decision['reasons'],'action_id':aid,'active_action':active or action_authorized,'authorize_action_requested':authorize_action,'complete_action_requested':complete_action,'clear_action_lock_requested':clear_action_lock,'action_authorized':action_authorized,'action_completed':action_completed,'duplicate_action':duplicate,'action_plan_written':plan_written,'action_lock_written':lock_written,'action_ledger_written':ledger_written,'recovery_snapshot_written':True,'dashboard_state_written':True,'command_execution_enabled':False,'automatic_action_execution_enabled':False,'continuous_loop_enabled':False,'windows_task_install_enabled':False,'paper_only':True,'read_only':True,'broker_write_enabled':False,'order_submission_enabled':False,'cancel_enabled':False,'replace_enabled':False,'position_close_enabled':False,'live_trading_enabled':False,'actual_credentials_used':False,'actual_external_network_used':False,'network_requests_executed':0,'write_requests_executed':0,'actual_paper_orders_submitted':0,'live_orders_submitted':0,'issue_count':len(issues),'blocking_issue_count':sum(1 for i in issues if i.get('blocking')),'issues':issues,'next_phase':'V83_05_LOCAL_ACTION_DISPATCHER' if state in {'ORCHESTRATOR_ACTION_READY','ORCHESTRATOR_ACTION_AUTHORIZED','ORCHESTRATOR_ACTION_COMPLETED','AUTOMATED_ORCHESTRATOR_WAIT'} else 'V83_01_TO_V83_04_WAIT_OR_RECOVER','validation_mode':'LOCAL_ORCHESTRATOR_DECISION_ONLY','observed_at':now,'result_path':str(result_path.resolve())}
    write_json(result_path,result); return result
