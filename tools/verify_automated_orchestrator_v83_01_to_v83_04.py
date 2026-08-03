import json
from pathlib import Path
R=Path(__file__).resolve().parents[1]; p=R/'release/v83_01_to_v83_04/actual/automated_orchestrator_result.json'
if not p.exists(): raise SystemExit('VERIFY=FAIL result missing')
r=json.loads(p.read_text(encoding='utf-8'))
checks=[r.get('status')=='PASS',r.get('paper_only') is True,r.get('read_only') is True,r.get('broker_write_enabled') is False,r.get('order_submission_enabled') is False,r.get('automatic_action_execution_enabled') is False,r.get('continuous_loop_enabled') is False,r.get('network_requests_executed')==0,r.get('write_requests_executed')==0,r.get('recovery_snapshot_written') is True,r.get('dashboard_state_written') is True]
if not all(checks): raise SystemExit('VERIFY=FAIL')
print('VERIFY=PASS')
