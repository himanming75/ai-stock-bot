$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

& $Python .\dashboard\patch_v3_2_1_git_discovery.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m py_compile .\dashboard\operations_dashboard_v3_2.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m unittest .\tests\test_operations_dashboard_v3_2_1.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
