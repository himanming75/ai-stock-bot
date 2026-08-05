param([string]$AccountIdKey="")

$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

Write-Host "EXPLICIT ETRADE SANDBOX READ"
Write-Host "NETWORK READ WILL OCCUR"
Write-Host "BROKER WRITE REMAINS OFF"

python `
    .\tools\run_etrade_sandbox_read_explicit.py `
    --account-id-key $AccountIdKey

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
