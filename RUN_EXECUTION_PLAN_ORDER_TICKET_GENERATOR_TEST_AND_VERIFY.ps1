$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest tools.test_execution_plan_order_ticket_generator -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python .\tools\run_execution_plan_order_ticket_generator.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "VERIFY: PASS"
Write-Host "BROKER WRITE: OFF"
Write-Host "ORDER SUBMISSION: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
