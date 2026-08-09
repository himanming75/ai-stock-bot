$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

& $Python -c "from pathlib import Path; t=Path('dashboard/operations_dashboard_v3_1.py').read_text(encoding='utf-8'); assert 'do_POST' not in t; assert 'TradingClient(' not in t; assert 'submit_order(' not in t; print('READ-ONLY STATIC CHECK: PASS')"
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -c "import sys; sys.path.insert(0,'.'); from dashboard.operations_dashboard_v3_1 import build_status; from pathlib import Path; s=build_status(Path(r'C:\stock-bot')); assert s['contracts']['read_only'] is True; assert s['contracts']['broker_write_performed'] is False; print('STATUS BUILD: PASS'); print('HEALTH:',s['health']['overall']); print('GATE:',s['runtime_gate']); print('TWO_WEEK:',s['two_week']); print('PAPER:',s['paper']); print('SHADOW:',s['shadow'])"
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "VERIFY: PASS"
