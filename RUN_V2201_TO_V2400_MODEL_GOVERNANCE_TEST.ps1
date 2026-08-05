$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_v2201_to_v2400_model_governance -v
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
Write-Host "TEST: PASS"
Write-Host "AUTOMATIC PROMOTION: OFF"
Write-Host "AUTOMATIC ROLLBACK: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
