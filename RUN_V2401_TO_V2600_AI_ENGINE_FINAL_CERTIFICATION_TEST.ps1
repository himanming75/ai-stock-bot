$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_v2401_to_v2600_ai_engine_final_certification -v
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
Write-Host "TEST: PASS"
Write-Host "AUTOMATIC PROMOTION: OFF"
Write-Host "CONTROLLER MODIFICATION: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
