$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

& $Python -c "import sys;sys.path.insert(0,'.');from dashboard.operations_dashboard_v3_2 import build_status;from pathlib import Path;s=build_status(Path(r'C:\stock-bot'));assert s['contracts']['read_only'];assert not s['contracts']['broker_write_performed'];assert not s['contracts']['order_submission_performed'];print('STATUS BUILD: PASS');print('HEALTH:',s['health']);print('GIT:',s['git']);print('TWO WEEK:',s['two_week'])"
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

$Health=".\runtime\dashboard_health_v3_3\latest_health_snapshot.json"
if(-not(Test-Path $Health)){throw "V3.3 HEALTH SNAPSHOT MISSING"}

$r=Get-Content $Health -Raw | ConvertFrom-Json
Write-Host "ALERT SUMMARY:" ($r.summary | ConvertTo-Json -Compress)
Write-Host "VERIFY: PASS"
