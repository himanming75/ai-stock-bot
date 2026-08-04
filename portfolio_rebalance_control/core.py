from __future__ import annotations
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path

def load(path):
    if not path.exists(): return {}
    try: v=json.loads(path.read_text(encoding='utf-8'))
    except Exception: return {}
    return v if isinstance(v,dict) else {}

def write(path,v):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n',encoding='utf-8')

def append(path,v):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8') as f:f.write(json.dumps(v,sort_keys=True)+'\n')

def digest(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def drift_rows(targets,currents,target_cash,current_cash,policy):
    t={str(x['strategy_id']):float(x.get('target_weight_pct',0)) for x in targets}
    c={str(x['strategy_id']):float(x.get('current_weight_pct',0)) for x in currents}
    t['CASH']=float(target_cash);c['CASH']=float(current_cash)
    ignore=float(policy.get('ignore_zone_pct',1));trigger=float(policy.get('rebalance_trigger_pct',3));critical=float(policy.get('critical_drift_pct',7.5))
    out=[]
    for sid in sorted(set(t)|set(c)):
        d=c.get(sid,0)-t.get(sid,0);a=abs(d)
        z='IGNORE' if a<ignore else 'BUFFER' if a<trigger else 'REBALANCE' if a<critical else 'CRITICAL'
        out.append({'strategy_id':sid,'target_weight_pct':round(t.get(sid,0),6),'current_weight_pct':round(c.get(sid,0),6),'drift_pct':round(d,6),'absolute_drift_pct':round(a,6),'drift_zone':z,'rebalance_required':z in {'REBALANCE','CRITICAL'}})
    return out

def adjustments(rows,equity,policy):
    frac=float(policy.get('incremental_rebalance_fraction',.5));mn=float(policy.get('minimum_adjustment_notional',100));mx=float(policy.get('maximum_adjustment_notional',20000))
    out=[]
    for r in rows:
        if not r['rebalance_required'] or r['strategy_id']=='CASH':continue
        req=equity*abs(r['drift_pct'])/100*frac;planned=min(req,mx)
        if planned<mn:continue
        out.append({'strategy_id':r['strategy_id'],'side':'SELL' if r['drift_pct']>0 else 'BUY','drift_zone':r['drift_zone'],'drift_pct':r['drift_pct'],'requested_notional':round(req,6),'planned_notional':round(planned,6),'submission_allowed':False,'state':'PLANNED'})
    return out

def controls(items,equity,cash,policy):
    mincash=float(policy.get('minimum_cash_pct',10));turn=float(policy.get('maximum_turnover_pct',20));required=equity*mincash/100
    sells=[dict(x) for x in items if x['side']=='SELL'];buys=sorted([dict(x) for x in items if x['side']=='BUY'],key=lambda x:abs(x['drift_pct']),reverse=True)
    sell_total=sum(x['planned_notional'] for x in sells);available=max(0,cash+sell_total-required);stage=sells[:]
    for x in buys:
        allowed=min(x['planned_notional'],available)
        if allowed<x['planned_notional']:
            x['state']='LIMITED_CASH_BUFFER' if allowed<=1e-9 else 'PARTIALLY_LIMITED_CASH_BUFFER';x['planned_notional']=round(allowed,6)
        stage.append(x);available-=allowed
    max_turn=equity*turn/100;remaining=max_turn;final=[]
    for x in sorted(stage,key=lambda x:(0 if x['side']=='SELL' else 1,-abs(x['drift_pct']))):
        allowed=min(float(x['planned_notional']),remaining)
        if allowed<float(x['planned_notional'])-1e-9:x['state']='LIMITED_TURNOVER' if allowed<=1e-9 else 'PARTIALLY_LIMITED_TURNOVER'
        x['planned_notional']=round(allowed,6);final.append(x);remaining-=allowed
    sells2=sum(x['planned_notional'] for x in final if x['side']=='SELL');buys2=sum(x['planned_notional'] for x in final if x['side']=='BUY');projected=cash+sells2-buys2;used=sells2+buys2
    return {'minimum_cash_pct':mincash,'required_cash':round(required,6),'projected_cash':round(projected,6),'projected_cash_pct':round(projected/equity*100 if equity else 0,6),'maximum_turnover_pct':turn,'used_turnover_notional':round(used,6),'used_turnover_pct':round(used/equity*100 if equity else 0,6),'adjustments':final}

def evaluate(root):
    policy=load(root/'release/v101_01_to_v101_32/input/rebalance_control_policy.json')
    portfolio=load(root/'release/v99_01_to_v99_32/actual/ai_portfolio_manager_result.json')
    account=load(root/'release/v96_01_to_v96_32/actual/paper_account_reconciliation_result.json')
    current=load(root/'release/v101_01_to_v101_32/input/current_strategy_weights.json')
    budget=load(root/'release/v100_33_to_v100_64/actual/risk_budget_allocation_result.json')
    if portfolio.get('state')!='AI_PORTFOLIO_MANAGER_READY' or budget.get('state')!='RISK_BUDGET_ALLOCATION_READY':
        return {'stage':'V101.32','stage_range':'V101.01-V101.32','state':'PORTFOLIO_REBALANCE_CONTROL_SOURCE_REQUIRED','status':'PASS','paper_only':True,'broker_write_enabled':False,'order_submission_enabled':False,'live_trading_enabled':False,'external_network_enabled':False}
    equity=float(account.get('equity_reconciliation',{}).get('reported_equity',0));cash=float(account.get('cash_reconciliation',{}).get('reported_ending_cash',0))
    rows=drift_rows(portfolio.get('allocation',{}).get('allocations',[]),current.get('allocations',[]),portfolio.get('allocation',{}).get('cash_weight_pct',0),current.get('cash_weight_pct',cash/equity*100 if equity else 0),policy)
    base=adjustments(rows,equity,policy);control=controls(base,equity,cash,policy);action=[x for x in control['adjustments'] if x['planned_notional']>0]
    checks={'snapshot_present':bool(rows),'cash_buffer_maintained':control['projected_cash_pct']>=float(policy.get('minimum_cash_pct',10))-1e-6,'turnover_limit':control['used_turnover_pct']<=float(policy.get('maximum_turnover_pct',20))+1e-6,'submission_disabled':all(x['submission_allowed'] is False for x in control['adjustments']),'count_limit':len(control['adjustments'])<=int(policy.get('maximum_adjustment_count',10))}
    failed=[k for k,v in checks.items() if not v];gate={'passed':not failed,'checks':checks,'failed':failed}
    state='PORTFOLIO_REBALANCE_CONTROL_READY' if gate['passed'] and action else 'PORTFOLIO_REBALANCE_CONTROL_NO_ACTION' if gate['passed'] else 'PORTFOLIO_REBALANCE_CONTROL_REVIEW_REQUIRED'
    observed=datetime.now(timezone.utc).isoformat();snapshot={'account_equity':round(equity,6),'account_cash':round(cash,6),'largest_absolute_drift_pct':max([x['absolute_drift_pct'] for x in rows] or [0]),'rebalance_required_count':sum(1 for x in rows if x['rebalance_required']),'drift_rows':rows}
    body={'stage':'V101.32','stage_range':'V101.01-V101.32','state':state,'status':'PASS','observed_at':observed,'rebalance_control_id':digest({'portfolio':portfolio.get('portfolio_id'),'budget':budget.get('risk_budget_id'),'snapshot':snapshot,'policy':policy})[:24],'source_portfolio_id':portfolio.get('portfolio_id'),'source_risk_budget_id':budget.get('risk_budget_id'),'account_equity':round(equity,6),'account_cash':round(cash,6),'snapshot':snapshot,'incremental_adjustments':base,'controls':control,'actionable_adjustment_count':len(action),'rebalance_gate':gate,'execution_authorized':False,'manual_approval_required':True,'actual_credentials_used':False,'actual_external_network_used':False,'actual_orders_submitted':0,'paper_only':True,'broker_write_enabled':False,'order_submission_enabled':False,'live_trading_enabled':False,'external_network_enabled':False,'next_phase':'V101_33_ADAPTIVE_REBALANCE_OPTIMIZATION'}
    body['rebalance_control_certificate_sha256']=digest(body)
    write(root/'release/v101_01_to_v101_32/actual/portfolio_rebalance_control_result.json',body);write(root/'release/v101_01_to_v101_32/actual/portfolio_rebalance_snapshot.json',snapshot)
    append(root/'release/v101_01_to_v101_32/actual/portfolio_rebalance_control_ledger.jsonl',{'observed_at':observed,'rebalance_control_id':body['rebalance_control_id'],'state':state,'largest_absolute_drift_pct':snapshot['largest_absolute_drift_pct'],'actionable_adjustment_count':len(action),'used_turnover_pct':control['used_turnover_pct'],'projected_cash_pct':control['projected_cash_pct'],'gate_passed':gate['passed']})
    return body
