$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
    tools.test_v6801_to_v7000_premarket_hardening `
    -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "PHASES 1-4 PREMARKET HARDENING: READY"
Write-Host "CLEANUP MODE: DRY RUN ONLY"
Write-Host "ETRADE MOCK WRITE: BLOCKED"
Write-Host "NETWORK: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
