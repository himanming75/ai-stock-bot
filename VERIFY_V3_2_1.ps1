$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

& $Python -c "import sys;sys.path.insert(0,'.');from dashboard.operations_dashboard_v3_2 import build_status;from pathlib import Path;s=build_status(Path(r'C:\stock-bot'));print('STATUS BUILD: PASS');print('GIT:',s['git']);print('HEALTH:',s['health']);print('ACCOUNT:',s['account']);print('POSITIONS:',len(s['positions']));print('OPEN ORDERS:',len(s['open_orders']));assert s['contracts']['read_only'];assert not s['contracts']['broker_write_performed'];assert not s['contracts']['order_submission_performed']"
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "VERIFY: PASS"
