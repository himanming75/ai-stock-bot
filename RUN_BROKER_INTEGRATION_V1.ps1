$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Python=if(Test-Path ".\.venv\Scripts\python.exe"){
 ".\.venv\Scripts\python.exe"
}else{
 "python"
}

$env:PYTHONPATH="C:\stock-bot"

Write-Host "========================================"
Write-Host " BROKER INTEGRATION V1.1 IMPORT REPAIR"
Write-Host "========================================"

& $Python .\dashboard\patch_broker_integration_v1_server.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\dashboard\patch_broker_integration_v1_ui.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m compileall -q .\broker_integration_v1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host ""
Write-Host "=== UNIT TESTS ==="

& $Python .\tests\test_broker_integration_v1.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host ""
Write-Host "=== SYNTHETIC READ-ONLY FIXTURE ==="

& $Python .\tests\run_broker_integration_v1_fixture.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host ""
Write-Host "RUN: PASS"
