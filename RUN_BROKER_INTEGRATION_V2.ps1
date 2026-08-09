$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

Write-Host "=== BROKER INTEGRATION V2 DEVELOPMENT ==="

& $Python .\dashboard\patch_broker_integration_v2_status.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\dashboard\patch_broker_integration_v2_server.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\dashboard\patch_broker_integration_v2_ui.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m compileall -q .\broker_integration_v1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\tests\test_broker_integration_v2.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
