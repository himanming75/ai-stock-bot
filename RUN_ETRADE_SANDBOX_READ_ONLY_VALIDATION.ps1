param([string]$Symbols="AAPL,MSFT")
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python `
  .\tools\run_etrade_sandbox_read_only_validation.py `
  --symbols $Symbols
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
Write-Host "READ ONLY VALIDATION: PASS"
Write-Host "BROKER WRITE: OFF"
Write-Host "ORDER SUBMISSION: OFF"
Write-Host "ORDER CANCEL: OFF"
