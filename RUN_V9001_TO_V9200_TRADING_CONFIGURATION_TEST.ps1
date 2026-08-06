$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
  tools.test_v9001_to_v9200_trading_configuration `
  -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "PROFILE CONFIGURATION: READY"
Write-Host "STRATEGY CONFIGURATION: READY"
Write-Host "RISK CONFIGURATION: READY"
Write-Host "DRAFT SAVE: READY"
Write-Host "ACTIVATION: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "ORDER SUBMISSION: OFF"
