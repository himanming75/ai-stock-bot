$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_v3801_to_v4000_etrade_sandbox_certification -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "TEST: PASS"
Write-Host "ACTUAL SANDBOX VALIDATION: DEFERRED"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
