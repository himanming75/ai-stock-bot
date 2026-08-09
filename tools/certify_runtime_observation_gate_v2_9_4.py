from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import argparse, json, subprocess

CERT=Path('runtime/regime_aware_buy_shadow_v2_9/latest_runtime_shadow_certification_v2_9.json')
OUT=Path('runtime/regime_aware_buy_shadow_v2_9_4/latest_runtime_observation_gate_v2_9_4.json')

def run(root:Path)->int:
    root=root.resolve(); py=root/'.venv/Scripts/python.exe'
    cmd=[str(py if py.exists() else 'python'), str(root/'tools/certify_runtime_shadow_v2_9.py'),'--root',str(root)]
    p=subprocess.run(cmd,cwd=root,capture_output=True,text=True,errors='replace',check=False)
    cert_path=root/CERT
    cert=json.loads(cert_path.read_text(encoding='utf-8-sig')) if cert_path.exists() else {}
    hook=cert.get('hook_observation',{}); shadow=cert.get('shadow_ledger',{}); rules=cert.get('certification_rules',{})
    integrity=(rules.get('structural_integrity_pass') is True and hook.get('parse_error_count',0)==0 and hook.get('primary_paper_flow_blocked_true_count',0)==0 and not shadow.get('duplicate_signal_ids') and not shadow.get('duplicate_outcome_ids') and not shadow.get('orphan_outcome_ids'))
    success=int(hook.get('successful_hook_count',0) or 0)
    if p.returncode!=0 or not integrity: status='BLOCKED_RUNTIME_OBSERVATION_INTEGRITY'
    elif success>=3: status='PASS_RUNTIME_OBSERVATION_GATE'
    else: status='PASS_WAITING_FOR_NEXT_SCHEDULED_RUNTIME'
    report={'stage':'V2.9.4_NEXT_SCHEDULED_RUNTIME_OBSERVATION_GATE','status':status,'generated_at_utc':datetime.now(timezone.utc).isoformat(),'reused_certifier':'tools/certify_runtime_shadow_v2_9.py','certifier_exit_code':p.returncode,'successful_hook_count':success,'required_successful_hooks':3,'remaining_successful_hooks':max(0,3-success),'certification_status':cert.get('status'),'hook_observation':hook,'shadow_ledger':shadow,'paper_session_observation':cert.get('paper_session_observation',{}),'contracts':{'paper_runtime_modified':False,'scheduled_task_modified':False,'paper_runtime_started_by_v2_9_4':False,'broker_write_performed':False,'paper_order_submission_performed':False,'live_order_submission_performed':False,'production_parameter_modified':False,'production_selector_modified':False,'duplicate_engine_created':False,'automatic_promotion':False}}
    out=root/OUT; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2)); return 2 if status.startswith('BLOCKED') else 0

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default=r'C:\stock-bot'); a=ap.parse_args(); return run(Path(a.root))
if __name__=='__main__': raise SystemExit(main())
