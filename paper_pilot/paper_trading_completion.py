from __future__ import annotations
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

def _load(path:Path)->dict[str,Any]:
    if not path.exists(): return {}
    v=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(v,dict): raise ValueError(f'JSON object required: {path}')
    return v

def _write(path:Path,payload:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')

def _sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()

class PaperTradingCompletionPackage:
    def run(self,*,policy_path:Path,pilot_result_path:Path,session_result_path:Path,performance_result_path:Path,risk_result_path:Path,automation_result_path:Path,validation_result_path:Path,analytics_result_path:Path,certificate_result_path:Path,promotion_result_path:Path,approval_result_path:Path,completion_manifest_path:Path,integrity_manifest_path:Path,dashboard_state_path:Path,result_path:Path)->dict[str,Any]:
        issues=[];loaded={}
        sources=(("POLICY",policy_path),("PILOT",pilot_result_path),("SESSION",session_result_path),("PERFORMANCE",performance_result_path),("RISK",risk_result_path),("AUTOMATION",automation_result_path),("VALIDATION",validation_result_path),("ANALYTICS",analytics_result_path),("CERTIFICATE",certificate_result_path),("PROMOTION",promotion_result_path),("APPROVAL",approval_result_path))
        for name,path in sources:
            try: payload=_load(path)
            except Exception as exc:
                payload={};issues.append({'code':f'INVALID_{name}_RESULT','blocking':True,'detail':str(exc)})
            if not payload: issues.append({'code':f'{name}_RESULT_NOT_FOUND','blocking':True,'detail':str(path)})
            loaded[name]=payload
        p=loaded['POLICY']
        if p:
            checks=[('PAPER_ONLY_REQUIRED',bool(p.get('paper_only'))),('READ_ONLY_REQUIRED',bool(p.get('read_only'))),('BROKER_WRITE_MUST_BE_DISABLED',not bool(p.get('broker_write_enabled',True))),('LIVE_TRADING_MUST_BE_DISABLED',not bool(p.get('live_trading_enabled',True))),('MINIMUM_VALIDATION_DAYS_INVALID',int(p.get('minimum_validation_days',0))>=5)]
            for code,passed in checks:
                if not passed:issues.append({'code':code,'blocking':True,'detail':'completion policy gate failed'})
        pilot,session,perf,risk,auto,val,ana,cert,promo,approval=[loaded[x] for x in ('PILOT','SESSION','PERFORMANCE','RISK','AUTOMATION','VALIDATION','ANALYTICS','CERTIFICATE','PROMOTION','APPROVAL')]
        days=int(val.get('validation_days',0) or 0);minimum=int(p.get('minimum_validation_days',5) or 5)
        gates={'pilot_running':bool(pilot.get('pilot_started') and pilot.get('state')=='CONTROLLED_PAPER_PILOT_RUNNING'),'session_healthy':session.get('health_status')=='HEALTHY','performance_ready':int(perf.get('sample_count',0) or 0)>=1,'risk_healthy':bool(risk.get('state')=='PAPER_RISK_HEALTHY' and not risk.get('emergency_stop_required',False)),'automation_ready':bool(auto.get('cycle_ready') and auto.get('recovery_gate_clear')),'validation_complete':bool(val.get('validation_complete') and days>=minimum),'analytics_complete':ana.get('state')=='VALIDATION_ANALYTICS_COMPLETE','certificate_verified':bool(cert.get('certificate_verified')),'promotion_ready':bool(promo.get('promotion_ready')),'approval_complete':bool(approval.get('certification_gate_clear'))}
        reasons=[]
        if days<minimum: reasons.append('MINIMUM_VALIDATION_DAYS_NOT_MET')
        for k,v in gates.items():
            if not v and k!='validation_complete':reasons.append(k.upper()+'_NOT_READY')
        if not gates['validation_complete']:reasons.append('MULTI_DAY_VALIDATION_NOT_COMPLETE')
        ready=all(gates.values()) and not any(i.get('blocking') for i in issues)
        if any(i.get('blocking') for i in issues):state,status='PAPER_TRADING_COMPLETION_SAFE_MODE','BLOCKED'
        elif days<minimum:state,status='WAIT_MULTI_DAY_VALIDATION','PASS'
        elif not ready:state,status='WAIT_FINAL_CERTIFICATION_GATES','PASS'
        else:state,status='PAPER_TRADING_COMPLETED','PASS'
        now=datetime.now(timezone.utc).isoformat()
        manifest={'stage_range':'V80.01-V80.04','package_type':'PAPER_TRADING_COMPLETION','state':state,'completion_ready':ready,'validation_days':days,'minimum_validation_days':minimum,'gates':gates,'wait_reasons':reasons,'pilot_id':pilot.get('pilot_id',''),'session_id':pilot.get('session_id',''),'certificate_id':cert.get('certificate_id',''),'approval_id':approval.get('approval_id',''),'paper_only':True,'broker_write_enabled':False,'live_trading_enabled':False,'created_at':now}
        _write(completion_manifest_path,manifest)
        paths=[pilot_result_path,session_result_path,performance_result_path,risk_result_path,automation_result_path,validation_result_path,analytics_result_path,certificate_result_path,promotion_result_path,approval_result_path,completion_manifest_path]
        entries=[{'path':str(x),'sha256':_sha(x),'size_bytes':x.stat().st_size} for x in paths if x.exists()]
        _write(integrity_manifest_path,{'stage':'V80.03','hash_algorithm':'SHA-256','file_count':len(entries),'files':entries,'integrity_ready':len(entries)==len(paths),'created_at':now})
        _write(dashboard_state_path,{'stage':'V80.04','completion_state':state,'completion_ready':ready,'validation_days':days,'minimum_validation_days':minimum,'progress_pct':round(min(100.0,days/minimum*100),8),'gates':gates,'wait_reasons':reasons,'integrity_file_count':len(entries),'paper_only':True,'broker_write_enabled':False,'live_trading_enabled':False,'observed_at':now})
        blocking=sum(1 for i in issues if i.get('blocking'))
        result={'stage_range':'V80.01-V80.04','implementation_type':'PAPER_TRADING_COMPLETION_PACKAGE','status':status,'state':state,'completion_ready':ready,'validation_days':days,'minimum_validation_days':minimum,'completion_progress_pct':round(min(100.0,days/minimum*100),8),'gates':gates,'wait_reasons':reasons,'completion_manifest_written':True,'integrity_manifest_written':True,'dashboard_state_written':True,'integrity_file_count':len(entries),'paper_only':True,'read_only':True,'broker_write_enabled':False,'order_submission_enabled':False,'cancel_enabled':False,'position_close_enabled':False,'continuous_loop_enabled':False,'live_trading_enabled':False,'actual_credentials_used':False,'actual_external_network_used':False,'network_requests_executed':0,'write_requests_executed':0,'actual_paper_orders_submitted':0,'live_orders_submitted':0,'safe_mode_engaged':blocking>0,'issue_count':len(issues),'blocking_issue_count':blocking,'issues':issues,'next_phase':'V81_SHADOW_TRADING_FOUNDATION' if ready else 'V80_CONTINUE_PAPER_VALIDATION','validation_mode':'LOCAL_PAPER_TRADING_COMPLETION_ONLY','observed_at':now,'result_path':str(result_path.resolve())}
        _write(result_path,result);return result
