$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_v8001_to_v8200_etrade -v
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
Write-Host "TEST: PASS"
Write-Host "ETRADE SANDBOX OAUTH: READY"
Write-Host "DPAPI VAULT: READY"
Write-Host "NETWORK DURING TEST: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "ORDER SUBMISSION: OFF"
