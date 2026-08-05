$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

Write-Host "EXPLICIT ETRADE PRODUCTION READ-ONLY"
Write-Host "NETWORK READ WILL OCCUR"
Write-Host "BROKER WRITE REMAINS OFF"

python `
    .\tools\run_etrade_production_read_explicit.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
