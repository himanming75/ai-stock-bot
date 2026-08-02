import json
from pathlib import Path
p=Path('release/v139_01/actual/actual_terminal_monitor_continuation_result.json')
if not p.is_file(): raise SystemExit('RESULT_NOT_FOUND')
d=json.loads(p.read_text(encoding='utf-8'))
assert d['stage']=='V139.01'
assert d['validation_mode']=='ACTUAL_SAVED_STATE_LOCAL_ONLY'
assert d['actual_external_network_used'] is False
assert d['actual_paper_orders_submitted']==0
assert d['live_orders_submitted']==0
assert d['network_requests_executed']==0
assert d['write_requests_executed']==0
assert d['state'] in {'WAIT_ACTIVE_ORDER','TERMINAL_OBSERVED','MONITOR_SAFE_MODE'}
print('VERIFY=PASS')
