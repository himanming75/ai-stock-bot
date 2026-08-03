import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'release/v80_01_to_v80_04/actual/paper_trading_completion_result.json'
if not p.exists():raise SystemExit('VERIFY=FAIL result missing')
r=json.loads(p.read_text(encoding='utf-8'))
c={'status':r.get('status')=='PASS','paper':r.get('paper_only') is True,'read_only':r.get('read_only') is True,'broker':r.get('broker_write_enabled') is False,'network':r.get('network_requests_executed')==0,'writes':r.get('write_requests_executed')==0,'manifest':r.get('completion_manifest_written') is True,'integrity':r.get('integrity_manifest_written') is True,'dashboard':r.get('dashboard_state_written') is True,'state':r.get('state') in {'WAIT_MULTI_DAY_VALIDATION','WAIT_FINAL_CERTIFICATION_GATES','PAPER_TRADING_COMPLETED'}}
f=[k for k,v in c.items() if not v]
if f:raise SystemExit('VERIFY=FAIL '+','.join(f))
print('VERIFY=PASS')
