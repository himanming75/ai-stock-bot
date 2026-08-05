$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_ai_approved_decision_execution_plan_bridge -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python .\tools\run_ai_approved_decision_execution_plan_bridge.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "VERIFY: PASS"
Write-Host "BROKER WRITE: OFF"
Write-Host "ORDER SUBMISSION: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
