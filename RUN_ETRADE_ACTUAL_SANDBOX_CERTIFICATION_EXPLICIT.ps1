$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "EXPLICIT ACTUAL ETRADE SANDBOX CERTIFICATION"
Write-Host "NETWORK READ WILL OCCUR"
Write-Host "BROKER WRITE REMAINS OFF"
python .\tools\run_etrade_actual_sandbox_certification_explicit.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
