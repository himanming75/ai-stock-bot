$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

& $Python .\dashboard\patch_v3_3_dashboard_html.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m py_compile .\dashboard\operations_dashboard_v3_2.py .\dashboard\health_snapshot_v3_3.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\dashboard\health_snapshot_v3_3.py --root C:\stock-bot --write
if($LASTEXITCODE -gt 2){exit $LASTEXITCODE}

& $Python -m unittest .\tests\test_dashboard_autostart_health_v3_3.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
